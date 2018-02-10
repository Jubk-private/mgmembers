from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

import csv
import os
import mgmembers.models as mgmodels

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MGMT_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(MGMT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, 'data')

FILENAME = os.path.join(DATA_DIR, r'Midguardians progress - Progress.csv')

OWNER_MAP = {
    'Kirstin': 'Miaw',
    'Walle': 'Svedin',
    'Zistus': 'Kerian',
}


class Command(BaseCommand):
    help = 'Imports MG-Members data from .csv file'

    def handle(self, *args, **options):
        with open(FILENAME, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')

            name_row = next(reader)
            index2data = {}
            for idx, val in enumerate(name_row):
                if not val:
                    continue
                index2data[idx] = {
                    'name': val,
                    'omen_clears': {},
                    'omen_wanted': [],
                    'woc_pops': {}
                }

            STATE_LOOKING = 0
            STATE_OMEN_CLEARS = 1
            STATE_WOC_POPS = 2
            STATE_OMEN_WANTED = 3

            state = STATE_LOOKING

            for row in reader:
                if state == STATE_LOOKING:
                    if row[0].startswith("Omen clear KIs obtained"):
                        state = STATE_OMEN_CLEARS
                        continue
                    elif row[0].startswith("Warder of Courage pop"):
                        state = STATE_WOC_POPS
                        continue
                    elif row[0].startswith("Omen scales wanted"):
                        state = STATE_OMEN_WANTED
                        continue

                if state == STATE_OMEN_CLEARS:
                    if not row[1]:
                        state = STATE_LOOKING
                        continue
                    boss = row[1].lower()
                    for idx in range(2, len(row)):
                        try:
                            data = index2data[idx]['omen_clears']
                        except KeyError:
                            continue
                        try:
                            data[boss] = True if row[idx] == "Yes" else False
                        except KeyError:
                            pass

                if state == STATE_OMEN_WANTED:
                    if not row[1]:
                        state = STATE_LOOKING
                        continue
                    boss = row[1].lower()
                    boss = boss[:boss.index(" ")]
                    for idx in range(2, len(row)):
                        try:
                            data = index2data[idx]['omen_wanted']
                        except KeyError:
                            continue
                        try:
                            if row[idx] == "Yes":
                                data.append(boss)
                        except KeyError:
                            pass

                if state == STATE_WOC_POPS:
                    if not row[1]:
                        state = STATE_LOOKING
                        continue
                    ki = row[1].lower()
                    ki = ki[:ki.index(" ")]
                    ki = ki + '_nazar'
                    for idx in range(2, len(row)):
                        try:
                            data = index2data[idx]['woc_pops']
                        except KeyError:
                            continue
                        try:
                            data[ki] = True if row[idx] == "Yes" else False
                        except KeyError:
                            pass
        for x in index2data.values():
            try:
                character = mgmodels.Character.objects.get(name=x['name'])
            except mgmodels.Character.DoesNotExist:
                continue

            if not hasattr(character, 'omenbosswishlist'):
                item = mgmodels.OmenBossWishlist(
                    character=character
                )
                values = x['omen_wanted']
                if len(values) > 0:
                    value = getattr(
                        mgmodels.OmenBossWishlist, values[0].upper()
                    )
                    if value is not None:
                        item.first_choice = value
                    if len(values) > 1:
                        value = getattr(
                            mgmodels.OmenBossWishlist, values[1].upper()
                        )
                        if value is not None:
                            item.second_choice = value
                item.save()

            if not hasattr(character, 'omenbossesclears'):
                item = mgmodels.OmenBossesClears(
                    character=character,
                    **x['omen_clears']
                )
                item.save()

            if not hasattr(character, 'warderofcouragepops'):
                item = mgmodels.WarderOfCouragePops(
                    character=character,
                    **x['woc_pops']
                )
                item.save()
