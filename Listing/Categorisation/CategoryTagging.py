import tld

domains = {}
catdomains = set()
categories = {}
with open('BigQuery-Top170k-NL-clean.csv', 'r') as inp:
    for line in inp:
        domains[tld.get_fld(line.split('\n')[0])] = line

with open('Tranco-202106-site_categories.csv', 'r') as cat:
    for line in cat:
        clear = line.split('\n')[0]
        url = clear.split('\t')[0]
        tags = clear.split('\t')[1].split(',')
        categories[url] = tags
        catdomains.add(url)

with open('BigQuery-McAfee-Cat.csv', 'w') as out:
    with open('BigQuery-McAfee-SpecialData.csv', 'w') as sens:
        intersect = set(domains.keys()).intersection(catdomains)
        for fld in intersect:
            s = categories[fld][0]
            for x in categories[fld][1:]:
                s += ',' + x
            if any([x in categories[fld] for x in
                    [' Auctions/Classifieds', ' Fashion/Beauty,', ' Gambling', ' Online Shopping']]):
                out.write(domains[fld].split('\n')[0] + ',' + s + '\n')
            if any([x in categories[fld] for x in
                    [' Drugs', ' Health,', ' Nudity', ' Pharmacy', ' Politics/Opinion',
                     ' Pornography', ' Religion/Ideology', ' Sexual Materials']]):
                sens.write(domains[fld].split('\n')[0] + ',' + s + '\n')
