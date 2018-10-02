#!/usr/bin/env python

# Python
import argparse
import logging
import sys
import textwrap
import yaml

# PyPoE
from PyPoE.poe.constants import MOD_DOMAIN, MOD_GENERATION_TYPE
from PyPoE.poe.file.dat import DatRecord, RelationalReader
from PyPoE.poe.file.ot import OTFileCache
from PyPoE.poe.file.translations import TranslationFileCache
from PyPoE.poe.sim.mods import get_translation, generate_spawnable_mod_list, SpawnChanceCalculator

class Mod():
    '''
    Proxy class for a DatRecord from the Mods.dat file.
    '''
    def __init__(self, mod_dat_record):
        self._dat_record = mod_dat_record


class ModExtractor:
    SPAWNABLE_MOD_GENERATION_TYPES = [
        MOD_GENERATION_TYPE.PREFIX,
        MOD_GENERATION_TYPE.SUFFIX,
        MOD_GENERATION_TYPE.CORRUPTED,
        MOD_GENERATION_TYPE.ENCHANTMENT
    ]

    ESSENCE_MODS_KEYS = {
        'Wand': 'Wand_ModsKey',
        'Dagger': '1Hand_ModsKey2',
        'Claw': '1Hand_ModsKey3',
        'One Hand Axe': '1Hand_ModsKey4',
        'One Hand Sword': '1Hand_ModsKey5',
        'Thrusting One Hand Sword': '1Hand_ModsKey6',
        'One Hand Mace': '1Hand_ModsKey7',
        'Sceptre': '1Hand_ModsKey8',
        'Bow': 'Bow_ModsKey',
        'Two Hand Axe': '2Hand_ModsKey2',
        'Two Hand Sword': '2Hand_ModsKey3',
        'Two Hand Mace': '2Hand_ModsKey4',
        'Fishing Rod': '2Hand_ModsKey5',
        'Ring': 'Ring_ModsKey',
        'Amulet': 'Amulet2_ModsKey',
        'Belt': 'Belt2_ModsKey',
        'Shield': 'Shield2_ModsKey',
        'Helmet': 'Helmet2_ModsKey',
        'Body Armour': 'BodyArmour2_ModsKey',
        'Boots': 'Boots2_ModsKey',
        'Gloves': 'Gloves2_ModsKey',
        'Quiver': 'Quiver_ModsKey'
    }

    def __init__(self, ggpk_path):
        reader_opts = {
            'use_dat_value': False,
            'auto_build_index': True
        }

        self.dat_reader = RelationalReader(path_or_ggpk=ggpk_path,
                                           read_options=reader_opts)
        self.ot_files = OTFileCache(path_or_ggpk=ggpk_path)
        self.translations = TranslationFileCache(path_or_ggpk=ggpk_path,
                                                 merge_with_custom_file=True)

    def get_item_mods(self, base_item_name):
        base_item_type = next((
            t for t in self.dat_reader['BaseItemTypes.dat']
            if t['Name'] == base_item_name
        ), None)

        if base_item_type is None:
            raise ValueError(f'could not find base item \'{base_item_name}\'')

        mods = []

        mods.extend(self._get_craftable_mods(base_item_type))
        mods.extend(self._get_essence_mods(base_item_type))
        mods.extend(self._get_spawnable_mods(base_item_type))

        return mods

    def get_mod_stats(self):
        print('=Base Item Types')

        for base_item_type in self.dat_reader['BaseItemTypes.dat']:
            item_name = base_item_type['Name']
            item_class = base_item_type['ItemClassesKey']['Id']
            item_category = base_item_type['ItemClassesKey']['Category']
            print(f'{item_name} | {item_class} | {item_category}', )

        print('=Essence Modifiers')

        for essence in self.dat_reader['Essences.dat']:
            print(f'{essence["BaseItemTypesKey"]["Name"]:}')
            for _, mods_key in self.ESSENCE_MODS_KEYS:
                mod = essence[mods_key]
                if mod is not None:
                    print(f'- {mods_key}: {mod["Id"]}')
                else:
                    print(f'- {mods_key}: {mod}')

    def get_strongbox_mods(self):
        strongbox_mods = []
        for strongbox in self.dat_reader['Strongboxes.dat']:
            chest = strongbox['ChestsKey']
            print(f'{chest["Name"]}:')
            print(f'- modifiers:')
            for mod in chest['ModsKeys']:
                print(f'  - {mod["Id"]}')
        return strongbox_mods

    def _get_craftable_mods(self, base_item_type):
        craftable_mods = []

        for opt in self.dat_reader['CraftingBenchOptions.dat']:
            if base_item_type['ItemClassesKey'] in opt['ItemClassesKeys']:
                mod_dat_record = opt['ModsKey']
                if mod_dat_record is not None:
                    mod = self._create_mod(mod_dat_record)
                    mod['master_name'] = opt['NPCMasterKey']['NPCsKey']['ShortName']
                    mod['master_level'] = opt['MasterLevel']
                    craftable_mods.append(mod)

        return craftable_mods

    def _get_essence_mods(self, base_item_type):
        item_class = base_item_type['ItemClassesKey']['Id']
        mods_key = self.ESSENCE_MODS_KEYS[item_class]

        essence_mods = []

        for ess in self.dat_reader['Essences.dat']:
            mod_dat_record = ess[mods_key]
            if mod_dat_record is not None and mod_dat_record['IsEssenceOnlyModifier']:
                mod = self._create_mod(mod_dat_record)
                mod['essence'] = ess['BaseItemTypesKey']['Name']
                essence_mods.append(mod)

        return essence_mods

    def _get_spawnable_mods(self, base_item_type):
        domain = self._get_mod_domain(base_item_type)
        tags = self._get_item_tags(base_item_type)

        spawnable_mods = []

        for gentype in self.SPAWNABLE_MOD_GENERATION_TYPES:
            mods = generate_spawnable_mod_list(self.dat_reader['Mods.dat'],
                                               domain, gentype, level=100,
                                               tags=tags)
            scc = SpawnChanceCalculator(mods, tags)

            for mod_dat_record in mods:
                mod = self._create_mod(mod_dat_record)
                mod['spawn_chance'] = '{:0.2%}'.format(scc.spawn_chance(mod_dat_record, remove=False))
                spawnable_mods.append(mod)

        return spawnable_mods

    def _create_mod(self, mod_dat_record):
        return {
            'id': mod_dat_record['Id'],
            'name': mod_dat_record['Name'],
            'group': mod_dat_record['CorrectGroup'],
            'domain': mod_dat_record['Domain'].name.lower(),
            'generation_type': mod_dat_record['GenerationType'].name.lower(),
            'effect_text': self._get_translation(mod_dat_record),
            'effect_text_generic': self._get_translation(mod_dat_record, use_placeholder=lambda _: '#'),
            'effect_values': self._get_translation(mod_dat_record, only_values=True),
            'is_essence_only': mod_dat_record['IsEssenceOnlyModifier']
        }

    def _get_translation(self, mod, **kwargs):
        translation_result = get_translation(mod, self.translations, **kwargs)

        if kwargs.get('only_values') is not None:
            values = [
                [[slot[0], slot[1]] if isinstance(slot, tuple) else [slot] for slot in line]
            for line in translation_result.values_parsed]
            return values
        else:
            return translation_result.lines

    def _get_item_tags(self, base_item_type):
        tags = base_item_type['TagsKeys']

        metadata_file = base_item_type['InheritsFrom'] + '.ot'
        parent_tags = self.ot_files[metadata_file]['Base']['tag'].keys()
        tags.extend(parent_tags)

        return tags

    def _get_mod_domain(self, base_item_type):
        default_domain = MOD_DOMAIN.ITEM
        item_class = base_item_type['ItemClassesKey']['Id']
        item_category = base_item_type['ItemClassesKey']['Category']

        if item_category == 'Flasks' or item_class == 'UtilityFlaskCritical':
            return MOD_DOMAIN.FLASK
        if item_class == 'Jewel':
            return MOD_DOMAIN.JEWEL
        if item_class == 'Leaguestone':
            return MOD_DOMAIN.LEAGUESTONE

        return default_domain


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
            Extract item modifiers from Path of Exile game data.
            Extracted data will be written to stdout in the YAML format.
            Example: ./%(prog)s PyPoE_Temp/ > mods.yaml
            '''))

    parser.add_argument('ggpk_path',
                        metavar='GGPK_CONTENT_PATH',
                        help='Path to a Content.ggpk file unpacked by PyPoE')
    parser.add_argument('--base_item',
                        metavar='BASE_ITEM_NAME',
                        help='Extract only modifiers for the given base item')

    args = parser.parse_args()
    mod_extractor = ModExtractor(args.ggpk_path)

    if args.base_item:
        item_mods = mod_extractor.get_item_mods(args.base_item)
        print(yaml.dump(item_mods, explicit_start=True))

    mod_extractor.get_strongbox_mods()


if __name__ == '__main__':
    main()
