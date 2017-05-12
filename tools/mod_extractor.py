#!/usr/bin/env python

# Python
from argparse import ArgumentParser
from itertools import groupby
from operator import itemgetter
from yaml import dump

# PyPoE
from PyPoE.poe.constants import MOD_DOMAIN, MOD_GENERATION_TYPE
from PyPoE.poe.file.dat import RelationalReader
from PyPoE.poe.file.translations import TranslationFileCache
from PyPoE.poe.sim.mods import get_translation, generate_spawnable_mod_list, SpawnChanceCalculator


ITEM_TYPES = {
    'one_handed_axe': {
        'tags': ['default', 'weapon', 'onehand', 'axe', 'one_hand_weapon']
    },
    'claw': {
        'tags': ['default', 'weapon', 'onehand', 'claw', 'one_hand_weapon']
    },
    'dagger': {
        'tags': ['default', 'weapon', 'onehand', 'dagger', 'one_hand_weapon']
    },
    'mace': {
        'tags': ['default', 'weapon', 'onehand', 'mace', 'one_hand_weapon']
    },
    'sceptre': {
        'tags': ['default', 'weapon', 'onehand', 'sceptre', 'one_hand_weapon']
    },
    'one_handed_sword': {
        'tags': ['default', 'weapon', 'onehand', 'sword', 'one_hand_weapon']
    },
    'one_handed_thrusting_sword': {
        'tags': ['default', 'weapon', 'onehand', 'sword', 'one_hand_weapon', 'rapier']
    },
    'wand': {
        'tags': ['default', 'weapon', 'onehand', 'wand', 'ranged', 'one_hand_weapon']
    },
    'two_handed_axe': {
        'tags': ['default', 'weapon', 'twohand', 'axe', 'two_hand_weapon']
    },
    'bow': {
        'tags': ['default', 'weapon', 'twohand', 'bow', 'ranged', 'two_hand_weapon']
    },
    'two_handed_mace': {
        'tags': ['default', 'weapon', 'twohand', 'mace', 'two_hand_weapon']
    },
    'staff': {
        'tags': ['default', 'weapon', 'twohand', 'staff', 'two_hand_weapon']
    },
    'two_handed_sword': {
        'tags': ['default', 'weapon', 'twohand', 'sword', 'two_hand_weapon']
    },
    'fishing_rod': {
        'tags': ['default', 'weapon', 'twohand', 'fishing_rod']
    },
    'str_body_armour': {
        'tags': ['default', 'armour', 'body_armour', 'str_armour']
    },
    'dex_body_armour': {
        'tags': ['default', 'armour', 'body_armour', 'dex_armour']
    },
    'int_body_armour': {
        'tags': ['default', 'armour', 'body_armour', 'int_armour']
    },
    'str_dex_body_armour': {
        'tags': ['default', 'armour', 'body_armour', 'str_dex_armour']
    },
    'str_int_body_armour': {
        'tags': ['default', 'armour', 'body_armour', 'str_int_armour']
    },
    'dex_int_body_armour': {
        'tags': ['default', 'armour', 'body_armour', 'dex_int_armour']
    },
    'str_helmet': {
        'tags': ['default', 'armour', 'helmet', 'str_armour']
    },
    'amulet': {
        'tags': ['default', 'amulet']
    },
    'str_jewel': {
        'tags': ['default', 'jewel', 'not_dex', 'not_int', 'strjewel']
    },
    'dex_jewel': {
        'tags': ['default', 'jewel', 'not_str', 'not_int', 'dexjewel']
    },
    'int_jewel': {
        'tags': ['default', 'jewel', 'not_dex', 'not_str', 'intjewel']
    },
}

MOD_GENERATION_TYPES = [
    MOD_GENERATION_TYPE.PREFIX,
    MOD_GENERATION_TYPE.SUFFIX,
    MOD_GENERATION_TYPE.CORRUPTED,
    MOD_GENERATION_TYPE.ENCHANTMENT
]

class ModReader:
    def __init__(self, ggpk_path):
        reader_opts = {'use_dat_value': False,'auto_build_index': True}

        self.reader = RelationalReader(path_or_ggpk=ggpk_path,
                                       raise_error_on_missing_relation=False,
                                       read_options=reader_opts)

        self.translations = TranslationFileCache(path_or_ggpk=ggpk_path)

    def get_mods(self, item_type):
        tags = self._get_item_tags(item_type)
        domain = self._get_mod_domain(item_type)

        result = {}

        for gentype in MOD_GENERATION_TYPES:
            mod_groups = self._get_mod_groups(domain, gentype, tags)
            result[gentype.name.lower() + '_mod_groups'] = mod_groups

        return result

    def _get_mod_groups(self, mod_domain, mod_generation_type, tags):
        mods = generate_spawnable_mod_list(self.reader['Mods.dat'], mod_domain,
                                           mod_generation_type, level=100,
                                           tags=tags)

        mods.sort(key=itemgetter('CorrectGroup'))

        scc = SpawnChanceCalculator(mods, tags)
        mod_groups = []

        for mod_group_id, mod_group in groupby(mods, key=itemgetter('CorrectGroup')):
            current_mod_group = {'id': mod_group_id}
            mod_groups.append(current_mod_group)
            for mod in mod_group:
                current_mod_group.setdefault('mods', []).append({
                    'id': mod['Id'],
                    'name': mod['Name'],
                    'effect_text': self._get_translation(mod),
                    'required_level': mod['Level'],
                    'spawn_weight': scc.get_spawn_weight(mod),
                    'spawn_chance': f'{scc.spawn_chance(mod, remove=False):.2%}'
                })
                current_mod_group.setdefault('effect_text', self._get_translation(mod, use_placeholder=lambda _: '#'))

        return mod_groups

    def _get_translation(self, mod, **kwargs):
        return ', '.join(get_translation(mod, self.translations, **kwargs).lines)

    def _get_item_tags(self, item_type):
        return ITEM_TYPES[item_type]['tags']

    def _get_mod_domain(self, item_type):
        if 'flask' in item_type:
            return MOD_DOMAIN.FLASK
        if 'leaguestone' in item_type:
            return MOD_DOMAIN.LEAGUESTONE
        if 'jewel' in item_type:
            return MOD_DOMAIN.JEWEL
        return MOD_DOMAIN.ITEM


def main():
    parser = ArgumentParser(description='Item modifiers -> YAML data')
    parser.add_argument('ggpk_path', metavar='GGPK_CONTENT_PATH',
            help='The path to the unpacked Content.ggpk')
    parser.add_argument('item_type', metavar='ITEM_TYPE',
            help='A type of weapon/armour/etc.')

    args = parser.parse_args()

    out = ModReader(args.ggpk_path).get_mods(args.item_type)

    print(dump(out, default_flow_style=False, indent=2))


if __name__ == '__main__':
    main()
