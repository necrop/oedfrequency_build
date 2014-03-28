"""
Pipeline - Runs processes for building OED frequency and currency data
"""

import os

import frequencyconfig


def dispatch():
    for function_name, status in frequencyconfig.PIPELINE:
        if status:
            print('=' * 30)
            print('Running "%s"...' % function_name)
            print('=' * 30)
            func = globals()[function_name]
            func()


def collect_entry_frequencies():
    from processors.frequencycollector import FrequencyCollector
    from processors.frequencyindexer import index_frequency_files
    fc = FrequencyCollector(out_dir=frequencyconfig.FREQUENCY_DIR,
                            terse=True, include_subentries=False)
    fc.process()

    index_frequency_files(
        frequencyconfig.FREQUENCY_DIR,
        os.path.join(frequencyconfig.FREQUENCY_DIR, 'index.xml')
    )


def collect_all_frequencies():
    from processors.frequencycollector import FrequencyCollector
    fc = FrequencyCollector(out_dir=frequencyconfig.FULL_FREQUENCY_DIR,
                            terse=True, include_subentries=True)
    fc.process()


def build_csv():
    from processors.xmltocsv import xml_to_csv
    xml_to_csv(frequencyconfig.FULL_FREQUENCY_DIR,
               frequencyconfig.CSV_FILE)


def analyse_frequency_data():
    from processors.frequencyanalysis import FrequencyAnalysis
    fa = FrequencyAnalysis(in_dir=frequencyconfig.FREQUENCY_DIR,
                           out_dir=frequencyconfig.ANALYSIS_DIR,)
    fa.analyse()
    fa.write()


def compare_with_oec():
    from processors.frequencyanalysis import OecComparison
    c = OecComparison(in_dir=frequencyconfig.ANALYSIS_DIR,
                      oec_file=frequencyconfig.OEC_FREQUENCY_FILE,)
    c.compare()


def pos_ratio():
    from processors.frequencyanalysis import PosRatios
    pr = PosRatios(in_dir=frequencyconfig.FREQUENCY_DIR,
                   out_dir=frequencyconfig.ANALYSIS_DIR,)
    pr.measure_ratios()


def rank_entries():
    from lex.oed.resources.entryrank import store_rankings
    store_rankings()


def raw_currency_data():
    from processors.currency import RawCurrencyData
    c = RawCurrencyData(in_dir=frequencyconfig.FREQUENCY_DIR)
    c.build_currency_data()
    c.write(os.path.join(frequencyconfig.CURRENCY_DIR, 'source_raw.csv'))


def estimate_currency():
    from processors.currency import CurrencyEvaluator
    c = CurrencyEvaluator(
        in_file=os.path.join(frequencyconfig.CURRENCY_DIR, 'source_raw.csv'),
    )
    c.read()
    c.write(os.path.join(frequencyconfig.CURRENCY_DIR, 'source.csv'))


def estimate_currency():
    from processors.currency import CurrencyEvaluator
    c = CurrencyEvaluator(
        in_file=os.path.join(frequencyconfig.CURRENCY_DIR, 'source_raw.csv'),
    )
    c.read()
    c.write(os.path.join(frequencyconfig.CURRENCY_DIR, 'source.csv'))


def ranksample():
    from processors.ranklist import rank_list
    rank_list(os.path.join(frequencyconfig.ANALYSIS_DIR, 'ranksample.txt'))

if __name__ == '__main__':
    dispatch()
