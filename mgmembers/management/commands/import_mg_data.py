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
                    'jobs': {}
                }

            STATE_LOOKING = 0
            STATE_JOBS = 1

            state = STATE_LOOKING

            for row in reader:
                if state == STATE_LOOKING:
                    if row[0] == "Jobs":
                        state = STATE_JOBS
                if state == STATE_JOBS:
                    if not row[1]:
                        state = STATE_LOOKING
                        break
                    job = row[1]
                    for idx in range(2, len(row)):
                        try:
                            data = index2data[idx]['jobs']
                        except KeyError:
                            continue
                        try:
                            val = row[idx]
                            if val == "Levelled":
                                data[job] = {'level': 99}
                            elif val.startswith("Primary"):
                                data[job] = {
                                    'level': 99,
                                    'event_status': 1,
                                    'gear_status': 1,
                                }
                                if val.endswith("(Mastered)"):
                                    data[job]['mastered'] = True
                            elif val.startswith("Secondary"):
                                data[job] = {
                                    'level': 99,
                                    'event_status': 2,
                                    'gear_status': 2,
                                }
                                if val.endswith("(Mastered)"):
                                    data[job]['mastered'] = True

                        except KeyError:
                            pass

            for x in index2data.values():
                ownername = OWNER_MAP.get(x['name'], x['name'])
                try:
                    owner = User.objects.get(username=ownername)
                except User.DoesNotExist:
                    print("Creating owner %s" % ownername)
                    owner = User(
                        username=ownername,
                        first_name=ownername
                    )
                    owner.save()
                # Don't bother with characters that already exist
                existing = mgmodels.Character.objects.filter(name=x['name'])
                if existing.count() > 0:
                    continue

                print("Creating character %s" % x['name'])
                char = mgmodels.Character(
                    owner=owner,
                    name=x['name']
                )
                char.save()
                for jobname, jobdata in iter(x['jobs'].items()):
                    cjob = mgmodels.CharacterJob(
                        character=char,
                        job=mgmodels.Job.objects.get(name=jobname)
                    )
                    for attr in (
                        'level', 'mastered', 'event_status', 'gear_status'
                    ):
                        if attr in jobdata:
                            setattr(cjob, attr, jobdata[attr])
                    cjob.save()
