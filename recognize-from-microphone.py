import os
import sys
import libs
import libs.fingerprint as fingerprint
import argparse
from argparse import RawTextHelpFormatter
from itertools import zip_longest
from termcolor import colored
from libs.config import get_config
from libs.reader_microphone import MicrophoneReader
from libs.visualiser_console import VisualiserConsole as visual_peak
from libs.visualiser_plot import VisualiserPlot as visual_plot
from libs.db_sqlite import SqliteDatabase
from libs.reader_file import FileReader

song = '/home/jagrati/audio-fingerprint-identifying-python/mp3/Baarishein.mp3'

r = FileReader(song)

data = r.parse_audio()
Fs = data['Fs']
num_channel = len(data['channels'])

result = set()
matches = []
db = SqliteDatabase()

def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return (list(filter(None, values)) for values in zip_longest(fillvalue=fillvalue, *args))

def find_matches(samples, Fs=fingerprint.DEFAULT_FS):
    hashes = list(fingerprint.fingerprint(samples, Fs=Fs))  # Ensure it returns a list
    return list(return_matches(hashes))  # Ensure it returns a list

def return_matches(hashes):
    mapper = {}
    for hash, offset in hashes:
        mapper[hash.upper()] = offset
    values = list(mapper.keys())

    for split_values in grouper(values, 1000):
        split_values_list = list(split_values)  # Convert filter object to list
        query = """
          SELECT upper(hash), song_fk, offset
          FROM fingerprints
          WHERE upper(hash) IN (%s)
        """ % ', '.join('?' * len(split_values_list))

        x = db.executeAll(query, split_values_list)
        matches_found = len(x)

        if matches_found > 0:
            msg = '   ** found %d hash matches (step %d/%d)' % (
                matches_found,
                len(split_values_list),
                len(values)
            )
            print(colored(msg, 'green'))
        else:
            msg = '   ** no matches found (step %d/%d)' % (
                len(split_values_list),
                len(values)
            )
            print(colored(msg, 'red'))

        for hash, sid, offset in x:
            yield (sid, offset - mapper[hash])

for channeln, channel in enumerate(data['channels']):
    matches.extend(find_matches(channel, Fs))

def align_matches(matches):
    diff_counter = {}
    largest = 0
    largest_count = 0
    song_id = -1

    for tup in matches:
        sid, diff = tup

        if diff not in diff_counter:
            diff_counter[diff] = {}

        if sid not in diff_counter[diff]:
            diff_counter[diff][sid] = 0

        diff_counter[diff][sid] += 1

        if diff_counter[diff][sid] > largest_count:
            largest = diff
            largest_count = diff_counter[diff][sid]
            song_id = sid

    songM = db.get_song_by_id(song_id)

    nseconds = round(float(largest) / fingerprint.DEFAULT_FS *
                     fingerprint.DEFAULT_WINDOW_SIZE *
                     fingerprint.DEFAULT_OVERLAP_RATIO, 5)

    return {
        "SONG_ID": song_id,
        "SONG_NAME": songM[1],
        "CONFIDENCE": largest_count,
        "OFFSET": int(largest),
        "OFFSET_SECS": nseconds
    }

total_matches_found = len(matches)

print('')

if total_matches_found > 0:
    msg = ' ** totally found %d hash matches'
    print(colored(msg, 'green') % total_matches_found)

    song = align_matches(matches)

    msg = ' => song: %s (id=%d)\n'
    msg += '    offset: %d (%d secs)\n'
    msg += '    confidence: %d'

    print(colored(msg, 'green') % (
        song['SONG_NAME'], song['SONG_ID'],
        song['OFFSET'], song['OFFSET_SECS'],
        song['CONFIDENCE']
    ))
else:
    msg = ' ** no matches found at all'
    print(colored(msg, 'red'))

db.close()  # Close the database connection

