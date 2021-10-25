with open('Corpus', 'r') as inp:
    with open('Tranco-P99J-202107.csv', 'r') as tranco:
        dictInput = {}
        for line in inp:
            dictInput[line.split('//')[1]] = line
        with open('Corpus-ranked', 'w') as output:
            for line in tranco:
                if line in dictInput:
                    output.write(dictInput[line])
                if f'www.{line}' in dictInput:
                    output.write(dictInput[f'www.{line}'])
