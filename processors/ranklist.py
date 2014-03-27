
from lex.oed.resources.entryrank import EntryRank

def rank_list(outfile):
    with open(outfile, 'w') as filehandle:
        for e, examples in EntryRank().rank_list_sample():
            row = '\t[%d, %0.3g, "%s"],\n' % (e.rank, e.frequency, _list_examples(examples),)
            filehandle.write(row)

def _list_examples(entries):
	return ', '.join([e.label for e in entries[0:3]])
