"""
Currency
"""

import math
import csv

from lex.oed.resources.vitalstatistics import VitalStatisticsCache
from lex.oed.resources.frequencyiterator import FrequencyIterator
import frequencyconfig


class RawCurrencyData(object):

    start = frequencyconfig.RANGE_START
    end = frequencyconfig.RANGE_END

    periods = ('1800-49', '1850-99', '1900-49', '1950-99', '2000-')
    headers = ['id', 'label', 'wordclass', 'header', 'subject', 'region',
               'usage', 'definition', 'start', 'end', 'quotations',
               'weighted size', 'ODO-linked', 'logically current']
    headers.extend(periods)
    headers.append('frequency change')

    # parameters for testing logical currency
    logical = {
        'date':  frequencyconfig.LOGICAL_CURRENCY_DATE,
        'size': frequencyconfig.LOGICAL_CURRENCY_SIZE,
        'suffixes1': ['-' + j for j in
                      frequencyconfig.LOGICAL_CURRENCY_SUFFIXES1.split('|')],
        'suffixes2': ['-' + j for j in
                      frequencyconfig.LOGICAL_CURRENCY_SUFFIXES1.split('|')],
    }

    def __init__(self, **kwargs):
        self.in_dir = kwargs.get('in_dir')

    def build_currency_data(self):
        self.vs = VitalStatisticsCache()
        iterator = FrequencyIterator(in_dir=self.in_dir,
                                     letters=None,
                                     message='Getting data')
        self.candidates = []
        self.candidates.append(list(RawCurrencyData.headers))
        for e in iterator.iterate():
            if (e.end and
                    e.end >= RawCurrencyData.start and
                    e.end <= RawCurrencyData.end and
                    not e.is_obsolete() and
                    not self.vs.find(e.id, field='revised') and
                    not e.lemma.startswith('-') and
                    not e.lemma.endswith('-')):
                if e.frequency_table() is not None:
                    freqs = [e.frequency_table().frequency(period=p)
                             for p in RawCurrencyData.periods]
                    delta = self.find_delta(e.frequency_table())
                else:
                    freqs = [float(0) for p in RawCurrencyData.periods]
                    delta = float(1)
                definition = e.definition or ''
                definition = '.' + definition

                row = [
                    e.id,
                    e.label,
                    e.wordclass(),
                    self.vs.find(e.id, field='header'),
                    self.vs.find(e.id, field='subject'),
                    self.vs.find(e.id, field='region'),
                    self.vs.find(e.id, field='usage'),
                    definition,
                    e.start,
                    e.end,
                    self.vs.find(e.id, field='quotations'),
                    self.vs.find(e.id, field='weighted_size'),
                    self.is_linked_to_odo(e),
                    self.is_logically_current(e),
                ]
                row.extend(['%0.2g' % f for f in freqs])
                row.append('%0.2g' % delta)
                self.candidates.append(tuple(row))

    def is_logically_current(self, e):
        etyma = self.vs.find(e.id, field='etyma')
        if len(etyma) == 2:
            if etyma[1][0] in RawCurrencyData.logical['suffixes1']:
                parent_id = etyma[0][1]
                tier = 'high'
            elif etyma[1][0] in RawCurrencyData.logical['suffixes2']:
                parent_id = etyma[0][1]
                tier = 'low'
            else:
                tier = None
            if (tier is not None and
                    (self.vs.find(parent_id, field='last_date') > RawCurrencyData.end or
                    (self.vs.find(parent_id, field='last_date') > RawCurrencyData.logical['date'] and
                    self.vs.find(parent_id, field='quotations') > RawCurrencyData.logical['size']))):
                return tier
        return None

    def is_linked_to_odo(self, e):
        if (self.vs.find(e.id, field='ode') is not None or
                self.vs.find(e.id, field='noad') is not None):
            return True
        else:
            return False

    def write(self, filepath):
        with open(filepath, 'w') as csvfile:
            csvw = csv.writer(csvfile)
            csvw.writerows(self.candidates)

    def find_delta(self, ft):
        f1 = ft.frequency(period='1800-99')
        f2 = ft.frequency(period='1950-99')
        if f1 == 0:
            d = float(1)
        elif f2 == 0:
            d = 0.0001 / f1
        else:
            d = f2 / f1
        if d < 1:
            d = -(1 / d)
        return d


class CurrencyEvaluator(object):

    def __init__(self, **kwargs):
        self.in_file = kwargs.get('in_file')

    def read(self):
        self.output = []
        with open(self.in_file, 'r') as csvfile:
            csvw = csv.reader(csvfile)
            for i, row in enumerate(csvw):
                if i == 0:
                    self.headers = row[:]
                    row2 = row[:]
                    row2.insert(12, 'log_weighted_size')
                    row2.extend(('delta score', 'obs label', 'pro',
                                 'pro reason', 'anti', 'anti reason', 'diff'))
                    self.output.append(row2)
                else:
                    d = {}
                    for f, v in zip(self.headers, row[:]):
                        d[f] = v
                    pro_score, pro_reason, anti_score, anti_reason,\
                        delta_score, log_weighted_size, obs_label =\
                        self.estimate_currency(d)
                    row2 = row[:]
                    row2.insert(12, '%0.2g' % log_weighted_size)
                    row2.extend(('%0.2g' % delta_score,
                                 obs_label,
                                 '%0.2g' % pro_score,
                                 pro_reason,
                                 '%0.2g' % anti_score,
                                 anti_reason,
                                 '%0.2g' % (pro_score - anti_score),))
                    self.output.append(row2)

    def write(self, filepath):
        with open(filepath, 'w') as csvfile:
            csvw = csv.writer(csvfile)
            csvw.writerows(self.output)

    def estimate_currency(self, d):
        for j in ('start', 'end', 'quotations', 'weighted size',
                  '1800-49', '1850-99', '1900-49', '1950-99', '2000-',
                  'frequency change'):
            d[j] = float(d[j])
        for j in ('ODO-linked', 'logically current'):
            if d[j].lower() == 'true':
                d[j] = True
            else:
                d[j] = False

        delta_score = d['frequency change']
        if delta_score < -5:
            delta_score = -5 - math.log(abs(delta_score))
        if delta_score > 5:
            delta_score = 5 + math.log(abs(delta_score))

        if d['weighted size'] == 0:
            log_weighted_size = 0
        else:
            log_weighted_size = math.log(d['weighted size'])

        pro = {}
        if d['logically current'] == 'high':
            pro['logical currency'] = 7
        if d['logically current'] == 'low':
            pro['logical currency'] = 3
        if d['ODO-linked']:
            pro['linked to ODE/NOAD'] = 9
        if d['subject']:
            pro['technical/specialist'] = 2
        if d['end'] and d['end'] > 1900:
            pro['last date'] = float(d['end'] - 1900) * 0.1
        #if delta_score > 1:
        #    pro['increase in frequency'] = abs(delta_score)
        if d['1950-99'] > 0.1:
            pro['high frequency'] = 10 * d['1950-99']
        if d['weighted size'] >= 4:
            pro['entry size'] = log_weighted_size

        anti= {}
        if delta_score < 0 and d['1950-99'] < 1:
            anti['decrease in frequency'] = abs(delta_score) * 0.5
        if d['1950-99'] < 0.0001:
            anti['low frequency'] = 0.002 / 0.0001
        elif d['1950-99'] < 0.002:
            anti['low frequency'] = 0.002 / d['1950-99']
        if d['end'] and d['end'] < 1850:
            anti['last date'] = float(1850 - d['end']) * 0.07
        if d['weighted size'] < 1 and d['weighted size'] > 0:
            anti['entry size'] = abs(log_weighted_size)

        if d['header'] == 'Obs.':
            anti['header text'] = 10
            obs_label = 'full'
        elif d['header'] == '? Obs.' or d['header'] == '?Obs.':
            anti['header text'] = 6
            obs_label = 'queried'
        elif ('nonce' in d['header'].lower() or
                'now rare' in d['header'].lower() or
                'Obs' in d['header']):
            anti['header text'] = 2
            obs_label = 'partial'
        else:
            obs_label = None

        if pro:
            pro_score = 2 + sum([v for v in pro.values()])
            pro_reason = max(pro.keys(), key=lambda k: pro[k])
        else:
            pro_score = 2
            pro_reason = ''

        if anti:
            anti_score = sum([v for v in anti.values()])
            anti_reason = max(anti.keys(), key=lambda k: anti[k])
        else:
            anti_score = 0
            anti_reason = ''

        return (pro_score, pro_reason, anti_score, anti_reason,
                delta_score, log_weighted_size, obs_label)
