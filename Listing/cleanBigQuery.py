import tld

seen = set()
with open('BigQuery-Top170k-NL.csv', 'r') as inp:
    with open('BigQuery-Top170k-NL-clean.csv', 'w') as out:
        for line in inp:
            url = tld.get_tld(line, as_object=True)
            subdomain = url.subdomain
            sliced_subdomain = ''
            fl_domain = tld.get_fld(line)
            if len(line.split('//')) < 2:
                print('found url without "//", things will break')
            scheme = line.split('//')[0] + '//'
            prefix = ''
            if 'www' in line.split('//')[1].split('.'):
                prefix = 'www.'
            for x in ['en', 'nl']:
                if x in subdomain.split('.'):
                    index = subdomain.split('.').index('en')
                    sliced_subdomain = '.'.join(subdomain.split('.')[index - 1:])
            if fl_domain not in seen:
                seen.add(fl_domain)
                seen.add(sliced_subdomain + fl_domain)
                out.write(scheme + prefix + sliced_subdomain + fl_domain + '\n')

    # checkDupes()
