with open('BigQuery-Top140K-NL-clean.csv', 'r') as bigQuery:
    with open('Tranco-P99J-202107.csv', 'r') as tranco:
        setTranco = set()
        setBigQuery = set()
        for line in tranco:
            setTranco.add(line)
        for line in bigQuery:
            setBigQuery.add(line) #TODO: change this to make line into first level domain
            #TODO: add first level domain as key, line as entry into dictionary
        matching = setBigQuery.intersection(setTranco)
        with open('matching.csv', 'w') as output:
            for x in matching:
                output.write(x) #TODO: for x in matching: output.write(dictionary[x])
