#!/usr/bin/env python

# Python
from argparse import ArgumentParser
from yaml import dump

# PyPoE
from PyPoE.poe.constants import MOD_DOMAIN, MOD_GENERATION_TYPE
from PyPoE.poe.file.dat import RelationalReader
from PyPoE.poe.file.translations import TranslationFileCache
from PyPoE.poe.sim.mods import get_translation, generate_spawnable_mod_list, SpawnChanceCalculator


MOD_CATEGORIES = {
        'one_handed_axe_mods': {
            'name': 'One-handed Axe Modifiers',
            'tags': ['default', 'weapon', 'onehand', 'axe', 'one_hand_weapon']
            },
        'claw_mods': {
            'name': 'Claw Modifiers',
            'tags': ['default', 'weapon', 'onehand', 'claw', 'one_hand_weapon']
            },
        'dagger_mods': {
            'name': 'Dagger Modifiers',
            'tags': ['default', 'weapon', 'onehand', 'dagger', 'one_hand_weapon']
            },
        'mace_mods': {
            'name': 'Mace Modifiers',
            'tags': ['default', 'weapon', 'onehand', 'mace', 'one_hand_weapon']
            },
        'sceptre_mods': {
            'name': 'Sceptre Modifiers',
            'tags': ['default', 'weapon', 'onehand', 'sceptre', 'one_hand_weapon']
            },
        'one_handed_sword_mods': {
            'name': 'One-handed Sword Modifiers',
            'tags': ['default', 'weapon', 'onehand', 'sword', 'one_hand_weapon']
            },
        'one_handed_thrusting_sword_mods': {
            'name': 'One-handed Thrusting Sword Modifiers',
            'tags': ['default', 'weapon', 'onehand', 'sword', 'one_hand_weapon', 'rapier']
            },
        'wand_mods': {
            'name': 'Wand Modifiers',
            'tags': ['default', 'weapon', 'onehand', 'wand', 'ranged', 'one_hand_weapon']
            },
        'two_handed_axe_mods': {
            'name': 'Two-handed Axe Modifier',
            'tags': ['default', 'weapon', 'twohand', 'axe', 'two_hand_weapon']
            },
        'bow_mods': {
            'name': 'Bow Modifiers',
            'tags': ['default', 'weapon', 'twohand', 'bow', 'ranged', 'two_hand_weapon']
            },
        'two_handed_mace_mods': {
            'name': 'Two-handed Mace Modifiers',
            'tags': ['default', 'weapon', 'twohand', 'mace', 'two_hand_weapon']
            },
        'staff_mods': {
            'name': 'Staff Modifiers',
            'tags': ['default', 'weapon', 'twohand', 'staff', 'two_hand_weapon']
            },
        'two_handed_sword_mods': {
            'name': 'Two-handed Sword Modifiers',
            'tags': ['default', 'weapon', 'twohand', 'sword', 'two_hand_weapon']
            },
        'fishing_rod_mods': {
            'name': 'Fishing Rod Modifiers',
            'tags': ['default', 'weapon', 'twohand', 'fishing_rod']
            },
        'str_body_armour_mods': {
            'name': 'Body Armour Modifiers (Str.)',
            'tags': ['default', 'armour', 'body_armour', 'str_armour']
            },
        'dex_body_armour_mods': {
            'name': 'Body Armour Modifiers (Dex.)',
            'tags': ['default', 'armour', 'body_armour', 'dex_armour']
            },
        'int_body_armour_mods': {
            'name': 'Body Armour Modifiers (Int.)',
            'tags': ['default', 'armour', 'body_armour', 'int_armour']
            },
        'str_dex_body_armour_mods': {
            'name': 'Body Armour Modifiers (Str./Dex.)',
            'tags': ['default', 'armour', 'body_armour', 'str_dex_armour']
            },
        'str_int_body_armour_mods': {
            'name': 'Body Armour Modifiers (Str./Int.)',
            'tags': ['default', 'armour', 'body_armour', 'str_int_armour']
            },
        'dex_int_body_armour_mods': {
            'name': 'Body Armour Modifiers (Dex./Int.)',
            'tags': ['default', 'armour', 'body_armour', 'dex_int_armour']
            },
        'str_helmet_mods': {
            'name': 'Helmet Modifiers (Str.)',
            'tags': ['default', 'armour', 'helmet', 'str_armour']
            },
        'amulet_mods': {
            'name': 'Amulet Modifiers',
            'tags': ['default', 'amulet']
            }
        'str_jewel_mods': {
            'name': 'Crimson Jewel Modifiers',
            'tags': ['default', 'jewel', 'not_dex', 'not_int', 'strjewel']
            },
        'dex_jewel_mods': {
            'name': 'Viridian Jewel Modifiers',
            'tags': ['default', 'jewel', 'not_str', 'not_int', 'dexjewel']
            },
        'int_jewel_mods': {
            'name': 'Cobalt Jewel Modifiers',
            'tags': ['default', 'jewel', 'not_dex', 'not_str', 'intjewel']
            },
        }


class ModReader:
    def __init__(self, ggpk_path):
        reader_opts = {'use_dat_value': False, 'auto_build_index': True}

        self.reader = RelationalReader(path_or_ggpk=ggpk_path,
                                       raise_error_on_missing_relation=False,
                                       read_options=reader_opts)

        self.translations = TranslationFileCache(path_or_ggpk=ggpk_path)

    def get_mods(self, mod_category):
        tag_list = MOD_CATEGORIES[mod_category]['tags']
        domain = self._get_mod_domain(mod_category)

        retval = {}

        generation_types = {
                'prefix': MOD_GENERATION_TYPE.PREFIX,
                'suffix': MOD_GENERATION_TYPE.SUFFIX,
                'corruption': MOD_GENERATION_TYPE.CORRUPTED
                }

        for mod_type_name in generation_types.keys():
            mod_list = generate_spawnable_mod_list(self.reader['Mods.dat'],
                                                   domain,
                                                   generation_types[mod_type_name],
                                                   level=100, tags=tag_list)

            scc = SpawnChanceCalculator(mod_list, tag_list)
            retval[mod_type_name] = []

            for mod in mod_list:
                mod_group = next(filter(lambda g: g['id'] == mod['CorrectGroup'], retval[mod_type_name]), None)
                if mod_group is None:
                    retval[mod_type_name].append({'id': mod['CorrectGroup'], 'mods': []})
                    mod_group = retval[mod_type_name][-1]
                    mod_group['name'] = ', '.join(get_translation(mod, self.translations, use_placeholder=True).lines)
                mod_group['mods'].append({
                        'id': mod['Id'],
                        'name': mod['Name'],
                        'description': ', '.join(get_translation(mod, self.translations).lines),
                        'level': mod['Level'],
                        'spawn_weight': scc.get_spawn_weight(mod),
                        'spawn_chance': "{:.2%}".format(scc.spawn_chance(mod, remove=False), 2)
                        })

        return retval

    def _get_mod_domain(self, mod_category):
        if 'flask' in mod_category:
            return MOD_DOMAIN.FLASK
        if 'leaguestone' in mod_category:
            return MOD_DOMAIN.LEAGUESTONE
        if 'jewel' in mod_category:
            return MOD_DOMAIN.JEWEL
        return MOD_DOMAIN.ITEM

def main():
    parser = ArgumentParser(description=':)')
    parser.add_argument('ggpk_path', metavar='GGPK_CONTENT_PATH',
            help='the path to the (unpacked) Content.ggpk')
    parser.add_argument('mod_category', metavar='MOD_CATEGORY',
            help='the category of mods to parse/print.')

    args = parser.parse_args()

    out = ModReader(args.ggpk_path).get_mods(args.mod_category)

    print('---')
    print('title: {}'.format(MOD_CATEGORIES[args.mod_category]['name']))
    print(dump(out, indent=2))
    print('---')

if __name__ == '__main__':
    main()
