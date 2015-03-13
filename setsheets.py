# Generate cheat sheets for sets of tunes
# Written by Stephan R.A. Deibel
# Jan 2015

import os, sys
import tempfile
import utils

def GenerateLargeSheets(tunes):

    set = utils.CTuneSet(tunes)

    abc = set.MakeNotesLarge()
    notes = utils.ABCToPostscript(abc)
    
    abc = set.MakeChordsLarge()
    chords = utils.ABCToPostscript(abc)
    
    return notes, chords

def GenerateSmallSheet(tunes):
    
    set = utils.CTuneSet(tunes)
    abc = set.MakeCardSmall()
    
    return utils.ABCToPostscript(abc)

if __name__ == '__main__':
    args = sys.argv[1:]

    # Generating a book
    if '--book' in args:
        args.remove('--book')
        if '--large' in args:
            args.remove('--large')
            name = args[0]
            book = utils.CBook(name, large=True)
            pages = book.GenerateLarge()
        elif '--ring' in args:
            args.remove('--ring')
            name = args[0]
            book = utils.CBook(name, large=True)
            pages = book.GenerateRing()
        else:
            name = args[0]
            book = utils.CBook(name)
            pages = book.GenerateSmall()

        cmd = 'open %s' % ' '.join(pages)
        os.system(cmd)

    # Generating a single pair of large-format pages
    elif '--large' in args:
        args.remove('--large')
        notes, chords = GenerateLargeSheets(args)
        cmd = 'open %s %s' % (notes, chords)
        os.system(cmd)
        
    # Generating a single small format page
    else:
        sheet = GenerateSmallSheet(args)
        cmd = 'open %s' % sheet
        os.system(cmd)
