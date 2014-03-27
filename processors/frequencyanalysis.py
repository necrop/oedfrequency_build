"""
FrequencyAnalysis
"""

import os
import re
from collections import defaultdict
import csv
from math import log

import numpy

from lex.oed.resources.frequencyiterator import FrequencyIterator
from lex.frequencytable import band_limits, sum_frequency_tables
from lex.oed.resources.vitalstatistics import VitalStatisticsCache


band_ranges = band_limits(mode='dictionary')
headers = {
    'band_distribution': ('band', 'range', 'num. entries'),
    'total_frequency': ('period', '% of corpus'),
    'high_frequency': ('entry', '1750-99', '1800-49', '1900-19',
                       '1950-59', 'modern'),
    'plural_to_singular': ('entry', 'frequency', 'ratio pl./sing.'),
    'high_frequency_rare': ('entry', 'frequency', 'header'),
    'frequency_to_size_high': ('entry', 'frequency', 'size', 'ratio'),
    'frequency_to_size_low': ('entry', 'frequency', 'size', 'ratio'),
}
headers['high_delta_up'] = headers['high_frequency']
headers['high_delta_down'] = headers['high_frequency']


class FrequencyAnalysis(object):

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get('in_dir')
        self.out_dir = kwargs.get('out_dir')

    def analyse(self):
        vs = VitalStatisticsCache()
        self.track = {
            'band_distribution': defaultdict(lambda: 0),
            'total_frequency': defaultdict(lambda: 0),
            'high_frequency': [],
            'high_delta_up': [],
            'high_delta_down': [],
            'delta_dist': defaultdict(lambda: 0),
            'plural_to_singular': [],
            'high_frequency_rare': [],
            'frequency_to_size_high': [],
            'frequency_to_size_low': [],
        }

        iterator = FrequencyIterator(in_dir=self.in_dir,
                                     letters=None,
                                     message='Analysing frequency data')
        for e in iterator.iterate():
            if not e.has_frequency_table():
                self.track['band_distribution'][16] += 1

            if e.has_frequency_table():
                ft = e.frequency_table()
                self.track['band_distribution'][ft.band(period='modern')] += 1

                if ft.band(period='modern') <= 5:
                    self.track['high_frequency'].append({
                        'label': e.label,
                        'id': e.id,
                        'ftable': ft
                    })

                if ft.frequency(period='modern') > 0.5 and e.start < 1750:
                    delta = ft.delta('1800-49', 'modern')
                    if delta is not None:
                        self.log_delta(delta, reciprocal=True)
                        if delta > 2:
                            self.track['high_delta_up'].append({
                                'label': e.label,
                                'id': e.id,
                                'ftable': ft
                            })

                if (ft.frequency(period='1800-49') > 0.5 and
                        not e.is_obsolete()):
                    delta = ft.delta('1800-49', 'modern')
                    if delta is not None and delta < 0.5:
                        self.track['high_delta_down'].append({
                            'label': e.label,
                            'id': e.id,
                            'ftable': ft
                        })
                        self.log_delta(delta)

                if not ' ' in e.lemma and not '-' in e.lemma:
                    for p in e.frequency_table().data.keys():
                        self.track['total_frequency'][p] +=\
                            ft.frequency(period=p)

                if (ft.frequency() > 0.01 and
                        self.is_marked_rare(vs.find(e.id, 'header'))):
                    self.track['high_frequency_rare'].append({
                        'label': e.label,
                        'id': e.id,
                        'header': vs.find(e.id, 'header'),
                        'fpm': ft.frequency()
                    })

                if ft.frequency() > 1:
                    self.compare_singular_to_plural(e)

                if ft.frequency() >= 0.0001 and vs.find(e.id, 'quotations') > 0:
                    ratio = log(ft.frequency()) / vs.find(e.id, 'quotations')
                    if ratio > 0.2:
                        self.track['frequency_to_size_high'].append({
                            'label': e.label,
                            'id': e.id,
                            'quotations': vs.find(e.id, 'quotations'),
                            'fpm': ft.frequency(),
                            'ratio': ratio,
                        })
                    if vs.find(e.id, 'quotations') >= 20:
                        self.track['frequency_to_size_low'].append({
                            'label': e.label,
                            'id': e.id,
                            'quotations': vs.find(e.id, 'quotations'),
                            'fpm': ft.frequency(),
                            'ratio': ratio,
                        })

    def compare_singular_to_plural(self, e):
        for wcs in e.wordclass_sets():
            if (wcs.wordclass == 'NN' and
                    wcs.frequency_table().frequency() > 1):
                groups = defaultdict(list)
                for type in wcs.types():
                    groups[type.wordclass].append(type)
                if 'NN' in groups and 'NNS' in groups:
                    summed_nn = sum_frequency_tables([t.frequency_table()
                        for t in groups['NN']
                        if t.frequency_table() is not None])
                    summed_nns = sum_frequency_tables([t.frequency_table()
                        for t in groups['NNS']
                        if t.frequency_table() is not None])
                    f_nn = summed_nn.frequency()
                    f_nns = summed_nns.frequency()
                    if f_nn and f_nns / f_nn > 1:
                        self.track['plural_to_singular'].append({
                            'label': e.label,
                            'id': e.id,
                            'fpm': wcs.frequency_table().frequency(),
                            'ratio': f_nns / f_nn
                        })

    def is_marked_rare(self, header):
        if (header is not None and
                len(header) < 100 and
                'rare' in header and
                not 'rarely' in header and
                not 'rare before' in header):
            return True
        else:
            return False

    def log_delta(self, delta, reciprocal=False):
        if delta is not None:
            if reciprocal and delta != 0:
                delta = 1 / delta
            delta = round(delta, 1)
            if delta > 2:
                delta = float(int(delta))
            if delta > 10:
                delta = float(10)
            self.track['delta_dist'][delta] += 1

    def write(self):
        for series in self.track.keys():
            rows = []
            if series in headers:
                rows.append(headers[series])

            if series == 'band_distribution':
                for b in sorted(self.track[series].keys()):
                    if not b in band_ranges:
                        label = 'n/a'
                    else:
                        label = band_ranges[b][2]
                    rows.append((b,
                                 label,
                                 int(self.track[series][b]), ))

            elif series == 'total_frequency':
                for p in sorted(self.track[series].keys()):
                    rows.append((p, int(self.track[series][p] / 10000),))

            elif series == 'delta_dist':
                for delta in sorted(self.track[series].keys()):
                    rows.append((delta, self.track[series][delta],))

            elif (series == 'high_frequency' or
                    series == 'high_delta_up' or
                    series == 'high_delta_down'):
                if series == 'high_frequency':
                    hf = sorted(self.track[series],
                                key=lambda e: e['ftable'].frequency(),
                                reverse=True)
                elif series == 'high_delta_up':
                    hf = sorted(self.track[series],
                                key=lambda e: e['ftable'].delta('1800-49', 'modern'),
                                reverse=True)
                elif series == 'high_delta_down':
                    hf = sorted(self.track[series],
                                key=lambda e: e['ftable'].delta('1800-49', 'modern'))
                if series == 'high_frequency':
                    hf = hf[:4999]
                else:
                    hf = hf[:999]
                for e in hf:
                    r = [e['label'],]
                    for p in ('1750-99', '1800-49', '1900-19', '1950-59', 'modern'):
                        r.append(e['ftable'].frequency(period=p))
                    rows.append(r)

            elif (series == 'frequency_to_size_high' or
                  series == 'frequency_to_size_low'):
                hf = sorted(self.track[series], key=lambda e: e['ratio'])
                if series == 'frequency_to_size_high':
                    hf.reverse()
                hf = hf[:999]
                for e in hf:
                    r = (e['label'], e['fpm'], e['quotations'], e['ratio'])
                    rows.append(r)

            elif series == 'plural_to_singular':
                hf = sorted(self.track[series],
                            key=lambda e: e['ratio'],
                            reverse=True)
                hf = hf[:999]
                for e in hf:
                    r = (e['label'], e['fpm'], '%.3g' % e['ratio'])
                    rows.append(r)

            elif series == 'high_frequency_rare':
                hf = sorted(self.track[series],
                            key=lambda e: e['fpm'],
                            reverse=True)
                hf = hf[:999]
                for e in hf:
                    r = (e['label'], e['fpm'], e['header'])
                    rows.append(r)

            filename = os.path.join(self.out_dir, '%s.csv' % series)
            with open(filename, 'w') as csvfile:
                csvw = csv.writer(csvfile)
                csvw.writerows(rows)


class OecComparison(object):

    def __init__(self, **kwargs):
        self.dir = kwargs.get('in_dir')
        self.oec_file = kwargs.get('oec_file')

    def compare(self):
        self.load_oec()
        self.load_oed()

        self.oed_lookup = {}
        for i in self.oed_rank:
            self.oed_lookup[i[0]] = i
        self.oec_lookup = {}
        for i in self.oec_rank:
            self.oec_lookup[i[0]] = i

        diffs = []
        for oec in self.oec_rank[:4999]:
            lemma = oec[0]
            if lemma in self.oed_lookup:
                oed = self.oed_lookup[lemma]
                f1 = log(oec[3])
                f2 = log(oed[3])
                diff = abs(f1 - f2)
                diffs.append((100 / f1) * diff)
                #pass
                print('%s  %d=%0.4g  |  %d=%0.4g' % (oec[0], oec[2], oec[3], oed[2], oed[3]))
                print((100 / f1) * diff)
            else:
                pass
                #print '%s  %d=%0.4g  |  NOT FOUND' % (oec[0], oec[2], oec[3])

        print(numpy.mean(diffs[:49]))
        print(numpy.mean(diffs[50:99]))
        print(numpy.mean(diffs[100:499]))
        print(numpy.mean(diffs[500:999]))
        print(numpy.mean(diffs[1000:1999]))
        print(numpy.mean(diffs[2000:2999]))
        print(numpy.mean(diffs[3000:4999]))

    def load_oed(self):
        self.oed_rank = []
        filename = os.path.join(self.dir, 'high_frequency.csv')
        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile)
            rank = 0
            seen = set()
            for i, row in enumerate(reader):
                if i > 0:
                    label = row[0]
                    lemma = re.sub(r', .*$', '', label)
                    if lemma[0].islower() and not lemma in seen:
                        rank += 1
                        f = float(row[6])
                        self.oed_rank.append((lemma, label, rank, f))
                        seen.add(lemma)

    def load_oec(self):
        self.oec_rank = []
        fh = open(self.oec_file, 'r')
        lines = [l.strip() for l in fh.readlines()
                 if '\t' in l]
        fh.close()

        rank = 0
        seen = set()
        for l in lines:
            label, f = l.split('\t')
            lemma = re.sub(r'-.$', '', label)
            if lemma[0].islower() and not lemma in seen:
                rank += 1
                f = f / 2460  # get frequency per million
                self.oec_rank.append((lemma, label, rank, f))
                seen.add(lemma)


class PosRatios(object):

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get('inDir')
        self.out_dir = kwargs.get('outDir')

    def measure_ratios(self):
        ratios = defaultdict(list)
        iterator = FrequencyIterator(in_dir=self.in_dir,
                                     letters=None,
                                     message='Analysing p.o.s. ratios')
        for e in iterator.iterate():
            for wcs in e.wordclass_sets():
                if ((wcs.wordclass == 'NN' or wcs.wordclass == 'VB') and
                    wcs.has_frequency_table()):
                    total = wcs.frequency_table().frequency()
                    local = defaultdict(lambda: 0)
                    for type in wcs.types():
                        if type.frequency_table().frequency() > 0:
                            local[type.wordclass] += type.frequency_table().frequency()
                    for wordclass, fpm in local.items():
                        ratios[wordclass].append(total / fpm)

        for wordclass in ratios:
            print('%s\t%0.4g' % (wordclass, numpy.median(ratios[wordclass])))
