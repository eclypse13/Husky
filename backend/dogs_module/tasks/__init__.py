# dogs_module/tasks/__init__.py

from .tasks_zooportal import (
    import_zooportal_dog_task,
    import_zooportal_page_task,
    import_zooportal_range_task,
)

from .tasks_breedarchive import (
    fetch_breedarchive_dog_task,
    fetch_full_pedigree_task,
    sync_breedarchive_recent_task,
    sync_breedarchive_browse_task,
    import_hybrid_full_dog_task,
    import_hybrid_full_page_task,
    import_hybrid_full_range_task,
    refresh_cookies_task,
)

from .tasks_ofa import (
    fetch_ofa_dog_task,
    fetch_ofa_bulk_by_reg_task,
    fetch_ofa_bulk_by_name_task,
    refresh_ofa_sh_breed_stats,
)

from .tasks_shows import (
    import_show_list_task,
    import_show_results_task,
    process_pending_results_task,
    process_all_pending_results_task,
    import_show_date_range_task,
    import_results_for_date_range_task,
    import_shows_full_task,
    recalculate_ratings_task,
)

from .tasks_coi import (
    recalculate_all_coi_task,
)

from .tasks_ml import (
    train_ml_model_task,
    predict_breeding_task,
)

from .tasks_photos import (
    photo_upload_one,
    photo_upload_bulk,
    photo_fetch_zoo_via_playwright,
    photo_fetch_zoo_bulk,
    photo_sync_yadisk_to_db,
    photo_stats,
    photo_delete_one,
    photo_backfill_hashes,
    photo_cleanup_placeholders,
)