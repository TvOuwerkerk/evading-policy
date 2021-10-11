with open('CRUX-McAfee-Cat_Lan.csv', 'r') as inp:
    with open('Corpus', 'a') as out:
        lines = inp.read().strip().split('\n')
        for line in lines:
            args = line.split(',')
            if str(args[1]) in ('en', 'nl'):
                out.write(args[0] + '\n')
