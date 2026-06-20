"""
Django management command: отчёт по обучающей выборке.

Использование:
    docker compose exec web python manage.py dataset_report
    docker compose exec web python manage.py dataset_report --augment --n-synthetic 2000
    docker compose exec web python manage.py dataset_report --export /tmp/dataset.csv
"""

import logging
from collections import Counter

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Отчёт по обучающему датасету: позитивы, негативы, покрытие, источники."

    def add_arguments(self, parser):
        parser.add_argument("--augment", action="store_true")
        parser.add_argument("--n-synthetic", type=int, default=2000)
        parser.add_argument("--export", type=str, default=None)

    def handle(self, *args, **opts):
        from ...services.dataset_builder import build_dataset, save_dataset_csv
        from ...models import MedicalRecord, Dog

        augment = opts["augment"]
        n_syn = opts["n_synthetic"]
        export_path = opts["export"]

        # === БЛОК 1: общие счётчики по БД ===
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== БЛОК 1. БАЗА ДАННЫХ ==="))
        total_dogs = Dog.objects.count()
        dogs_with_parents = Dog.objects.exclude(sire__isnull=True).exclude(dam__isnull=True).count()
        total_records = MedicalRecord.objects.count()
        self.stdout.write(f"Всего собак в БД:                  {total_dogs}")
        self.stdout.write(f"Собак с обоими родителями:         {dogs_with_parents}")
        self.stdout.write(f"Всего MedicalRecord-записей:       {total_records}")

        registry_counts = Counter()
        conclusion_counts = Counter()
        source_counts = Counter()
        for r in MedicalRecord.objects.values("registry", "conclusion", "source"):
            registry_counts[(r["registry"] or "").upper()] += 1
            conclusion_counts[(r["conclusion"] or "").upper()] += 1
            source_counts[(r["source"] or "").lower()] += 1

        self.stdout.write("\nПо типам анализов:")
        for reg, n in registry_counts.most_common():
            self.stdout.write(f"  {reg:<40} {n}")

        self.stdout.write("\nПо заключениям:")
        for c, n in conclusion_counts.most_common(10):
            self.stdout.write(f"  {c:<20} {n}")

        self.stdout.write("\nПо источникам:")
        for src, n in source_counts.most_common():
            self.stdout.write(f"  {src:<20} {n}")

        # === БЛОК 2: реальная выборка ===
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== БЛОК 2. ОБУЧАЮЩАЯ ВЫБОРКА ==="))
        real = build_dataset(augment=False)
        if not real:
            self.stdout.write(self.style.WARNING("Реальной выборки нет"))
            return

        n_real = len(real)
        # Учитываем что метки могут быть None
        hip_labeled = [d for d in real if d.get("offspring_has_hip_problem") is not None]
        eye_labeled = [d for d in real if d.get("offspring_has_eye_problem") is not None]
        hip_pos = sum(d["offspring_has_hip_problem"] for d in hip_labeled)
        eye_pos = sum(d["offspring_has_eye_problem"] for d in eye_labeled)

        self.stdout.write(f"Реальных пар родители-потомок:     {n_real}")
        self.stdout.write(f"  • С меткой по бёдрам:            {len(hip_labeled)}")
        self.stdout.write(f"      позитивов:                    {hip_pos} "
                          f"({hip_pos / max(len(hip_labeled), 1):.1%})")
        self.stdout.write(f"  • С меткой по глазам:            {len(eye_labeled)}")
        self.stdout.write(f"      позитивов:                    {eye_pos} "
                          f"({eye_pos / max(len(eye_labeled), 1):.1%})")

        # Покрытие признаков
        feature_keys = [k for k in real[0].keys()
                        if not k.startswith("_") and not k.startswith("offspring_has_")]
        coverage = {}
        for key in feature_keys:
            filled = sum(1 for r in real if r.get(key) is not None)
            coverage[key] = filled / n_real

        self.stdout.write("\nПокрытие ключевых признаков (% непустых):")
        important = ["sire_hips", "dam_hips", "sire_eyes", "dam_eyes",
                     "sire_coi", "dam_coi", "pair_coi", "avg_hip_score"]
        for k in important:
            if k in coverage:
                self.stdout.write(f"  {k:<35} {coverage[k]:.1%}")

        self.stdout.write("\nПокрытие агрегатов по предкам:")
        anc_keys = sorted([k for k in feature_keys if "_anc_" in k])
        for k in anc_keys:
            self.stdout.write(f"  {k:<45} {coverage.get(k, 0):.1%}")

        # === БЛОК 3: синтетика + итог ===
        if augment:
            self.stdout.write(self.style.MIGRATE_HEADING("\n=== БЛОК 3. СИНТЕТИКА ==="))
            combined = build_dataset(augment=True, n_synthetic=n_syn)
            synthetic = [r for r in combined if r.get("_synthetic")]
            n_syn_actual = len(synthetic)
            hip_syn_lab = [d for d in synthetic if d.get("offspring_has_hip_problem") is not None]
            eye_syn_lab = [d for d in synthetic if d.get("offspring_has_eye_problem") is not None]
            hip_syn = sum(d["offspring_has_hip_problem"] for d in hip_syn_lab)
            eye_syn = sum(d["offspring_has_eye_problem"] for d in eye_syn_lab)

            self.stdout.write(f"Синтетических примеров: {n_syn_actual}")
            self.stdout.write(f"  • Позитивов hip: {hip_syn} "
                              f"({hip_syn / max(n_syn_actual, 1):.1%})")
            self.stdout.write(f"  • Позитивов eye: {eye_syn} "
                              f"({eye_syn / max(n_syn_actual, 1):.1%})")

            self.stdout.write(self.style.MIGRATE_HEADING("\n=== БЛОК 4. ИТОГОВЫЕ ВЫБОРКИ ПО МОДЕЛЯМ ==="))
            hip_lab_all = [d for d in combined if d.get("offspring_has_hip_problem") is not None]
            eye_lab_all = [d for d in combined if d.get("offspring_has_eye_problem") is not None]
            hip_total = sum(d["offspring_has_hip_problem"] for d in hip_lab_all)
            eye_total = sum(d["offspring_has_eye_problem"] for d in eye_lab_all)

            self.stdout.write(f"Модель HIP:")
            self.stdout.write(f"  всего записей: {len(hip_lab_all)}")
            self.stdout.write(f"  позитивов: {hip_total} "
                              f"({hip_total / max(len(hip_lab_all), 1):.2%})")
            self.stdout.write(f"\nМодель EYE:")
            self.stdout.write(f"  всего записей: {len(eye_lab_all)}")
            self.stdout.write(f"  позитивов: {eye_total} "
                              f"({eye_total / max(len(eye_lab_all), 1):.2%})")

        if export_path:
            path = save_dataset_csv(path=export_path, augment=augment)
            if path:
                self.stdout.write(self.style.SUCCESS(f"\nДатасет экспортирован: {path}"))

        self.stdout.write(self.style.SUCCESS("\nГотово."))
