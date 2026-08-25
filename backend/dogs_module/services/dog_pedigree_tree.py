"""
Дерево родословной (предки dam/sire) собаки.
"""
from typing import Optional

from ..models import Dog
from ..utils.dog_utils import best_dog_photo_url


PEDIGREE_FIELDS = [
    'id', 'uuid', 'registered_name', 'call_name', 'sex',
    'year_of_birth', 'date_of_birth', 'photo_url', 'photo_yadisk_path',
    'color', 'land_of_birth', 'prefix_titles', 'suffix_titles', 'coi',
    'dam_id', 'sire_id',
]

def build_pedigree_tree(root_dog: Dog, max_depth: int) -> dict:
    by_id = {root_dog.id: root_dog}
    frontier_ids = {root_dog.id}
    depth = 0

    while frontier_ids and depth < max_depth:
        parent_ids = set()
        for did in frontier_ids:
            d = by_id[did]
            if d.dam_id and d.dam_id not in by_id:
                parent_ids.add(d.dam_id)
            if d.sire_id and d.sire_id not in by_id:
                parent_ids.add(d.sire_id)
        if not parent_ids:
            break
        fetched = Dog.objects.using('dogs_db').filter(id__in=parent_ids).only(*PEDIGREE_FIELDS)
        for dog in fetched:
            by_id[dog.id] = dog
        frontier_ids = parent_ids
        depth += 1

    def to_node(dog_id, remaining):
        if not dog_id or dog_id not in by_id:
            return None
        d = by_id[dog_id]
        return {
            'id': d.id,
            'uuid': d.uuid,
            'display_name': d.display_name,
            'registered_name': d.registered_name,
            'call_name': d.call_name,
            'sex': d.sex,
            'year_of_birth': d.year_of_birth,
            'date_of_birth': d.date_of_birth,
            'photo_url': d.photo_url,
            'dog_photo': best_dog_photo_url(d),
            'color': d.color,
            'land_of_birth': d.land_of_birth,
            'prefix_titles': d.prefix_titles,
            'suffix_titles': d.suffix_titles,
            'coi': d.coi,
            'dam': to_node(d.dam_id, remaining - 1) if remaining > 0 else None,
            'sire': to_node(d.sire_id, remaining - 1) if remaining > 0 else None,
        }

    return to_node(root_dog.id, max_depth)
