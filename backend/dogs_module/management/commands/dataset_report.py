"""
Django management command: отчёт по обучающей выборке.

Показывает:
  • объём реальных данных, объём синтетики
  • распределение позитивов / негативов
  • покрытие предков (для агрегатов BFS)
  • покрытие COI
  • топ источников медзаписей

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
        parser.add_argument("--augment", action="store_true",
                            help="Добавить синтетику в отчёт (как при обучении)")
        parser.add_argument("--n-synthetic", type=int, default=2000,
                            help="Сколько синтетических примеров добавлять")
        parser.add_argument("--export", type=str, default=None,
                            help="Путь для экспорта датасета в CSV")

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
        self.stdout.write(f"Всего собак в БД: {total_dogs}")
        self.stdout.write(f"Собак с обоими родителями: {dogs_with_parents}")
        self.stdout.write(f"Всего MedicalRecord-записей: {total_records}")

        # Распределение по типам анализов
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
        hip_pos = sum(d["offspring_has_hip_problem"] for d in real)
        eye_pos = sum(d["offspring_has_eye_problem"] for d in real)
        self.stdout.write(f"Реальных пар родители-потомок: {n_real}")
        self.stdout.write(f"  • Позитивов hip (Borderline+): {hip_pos} ({hip_pos / n_real:.1%})")
        self.stdout.write(f"  • Позитивов eye (AFFECTED): {eye_pos} ({eye_pos / n_real:.1%})")

        # Покрытие признаков
        feature_keys = [k for k in real[0].keys() if not k.startswith("_") and not k.startswith("offspring_has_")]
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

        # Агрегаты предков — отдельно
        self.stdout.write("\nПокрытие агрегатов по предкам:")
        anc_keys = sorted([k for k in feature_keys if "_anc_" in k])
        for k in anc_keys:
            self.stdout.write(f"  {k:<45} {coverage.get(k, 0):.1%}")

        # === БЛОК 3: синтетика ===
        if augment:
            self.stdout.write(self.style.MIGRATE_HEADING("\n=== БЛОК 3. СИНТЕТИКА ==="))
            combined = build_dataset(augment=True, n_synthetic=n_syn)
            synthetic = [r for r in combined if r.get("_synthetic")]
            n_syn_actual = len(synthetic)
            hip_syn = sum(d["offspring_has_hip_problem"] for d in synthetic)
            eye_syn = sum(d["offspring_has_eye_problem"] for d in synthetic)

            self.stdout.write(f"Синтетических примеров: {n_syn_actual}")
            self.stdout.write(f"  • Позитивов hip: {hip_syn} ({hip_syn / n_syn_actual:.1%})")
            self.stdout.write(f"  • Позитивов eye: {eye_syn} ({eye_syn / n_syn_actual:.1%})")

            n_total = len(combined)
            hip_total = hip_pos + hip_syn
            eye_total = eye_pos + eye_syn
            self.stdout.write(self.style.MIGRATE_HEADING("\n=== БЛОК 4. ИТОГОВАЯ ВЫБОРКА ==="))
            self.stdout.write(f"Реальные: {n_real:>5}  ({n_real / n_total:.1%})")
            self.stdout.write(f"Синтетические: {n_syn_actual:>5}  ({n_syn_actual / n_total:.1%})")
            self.stdout.write(f"ИТОГО: {n_total:>5}")
            self.stdout.write(f"  Позитивов hip: {hip_total:>5}  ({hip_total / n_total:.2%})")
            self.stdout.write(f"  Позитивов eye: {eye_total:>5}  ({eye_total / n_total:.2%})")

        if export_path:
            path = save_dataset_csv(path=export_path, augment=augment)
            if path:
                self.stdout.write(self.style.SUCCESS(f"\nДатасет экспортирован: {path}"))

        self.stdout.write(self.style.SUCCESS("\nГотово."))
