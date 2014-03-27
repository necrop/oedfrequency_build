"""
frequencyconfig -- configuration for building OED frequency and currency data
"""

import os
from lex import lexconfig

PIPELINE = [
    ('collect_entry_frequencies', 1),
    ('collect_all_frequencies', 1),
    # analysis of the frequency output
    ('analyse_frequency_data', 0),
    ('compare_with_oec', 0),
    ('pos_ratio', 0),
    ('rank_entries', 0),
    ('ranksample', 0),
    # currency
    ('raw_currency_data', 1),
    ('estimate_currency', 1),
]

OED_ROOT = lexconfig.OED_DIR
PROJECT_ROOT = os.path.join(OED_ROOT, 'projects', 'frequency')

FREQUENCY_DIR = lexconfig.OED_FREQUENCY_DIR
FULL_FREQUENCY_DIR = os.path.join(PROJECT_ROOT, 'full_frequency_data')
ANALYSIS_DIR = os.path.join(PROJECT_ROOT, 'analysis')
RANKING_FILE = os.path.join(ANALYSIS_DIR, 'ranking.csv')
CURRENCY_DIR = os.path.join(PROJECT_ROOT, 'currency')
OEC_FREQUENCY_FILE = os.path.join(lexconfig.GEL_DIR, 'resources', 'oec',
                                  'oec_lempos_frequencies.txt')

# Only entries with last dates between range_start and range_end will
#  be evaluated.
RANGE_START = 1700
RANGE_END = 1950

# Logical currency for a derivative requires the etymon to have either:
#  - a last date after range_end;
#  - OR a last date after logical_currency_date and size (number of
#    quotations) greater than logical_currency_size.
LOGICAL_CURRENCY_DATE = 1850
LOGICAL_CURRENCY_SIZE = 20
LOGICAL_CURRENCY_SUFFIXES1 = 'ing|ed|ness'
LOGICAL_CURRENCY_SUFFIXES2 = 'less|able|ly'
