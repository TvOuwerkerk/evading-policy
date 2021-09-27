import tld

domains = {}
catdomains = set()
categories = {}
with open('..\\CRUX-Top170K-NL-clean.csv', 'r') as inp:
    for line in inp:
        domains[tld.get_fld(line.split('\n')[0])] = line

with open('Tranco-202106-site_categories.csv', 'r') as cat:
    for line in cat:
        clear = line.split('\n')[0]
        url = clear.split('\t')[0]
        tags = clear.split('\t')[1].split(',')
        categories[url] = tags
        catdomains.add(url)

with open('CRUX-McAfee-Cat.csv', 'w') as out:
    intersect = set(domains.keys()).intersection(catdomains)
    for fld in intersect:
        s = categories[fld][0]
        for x in categories[fld][1:]:
            s += ',' + x
        if any([x in categories[fld] for x in
                [' Auctions/Classifieds', ' Fashion/Beauty,', ' Gambling', ' Online Shopping']]):
            out.write(domains[fld].split('\n')[0] + ',' + s + '\n')
