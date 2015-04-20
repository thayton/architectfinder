#!/usr/bin/env python                                                                                                                                                                
"""
Python script for scraping the results from http://architectfinder.aia.org/frmSearch.aspx
"""

__author__ = 'Todd Hayton'

import re
import urlparse
import mechanize

from bs4 import BeautifulSoup, Comment, Tag

def soupify(page):
    s = BeautifulSoup(page)

    # Remove unwanted tags
    tags = s.findAll(lambda tag: tag.name == 'script' or \
                                 tag.name == 'style')
    for t in tags:
        t.extract()
        
    # Remove comments
    comments = s.findAll(text=lambda text:isinstance(text, Comment))
    for c in comments:
        c.extract()

    return s

class ArchitectFinderScraper(object):
    def __init__(self):
        self.url = "http://architectfinder.aia.org/frmSearch.aspx"
        self.br = mechanize.Browser()
        self.br.addheaders = [('User-agent', 
                               'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.63 Safari/535.7')]

    def get_state_items(self):
        self.br.open(self.url)
        self.br.select_form('aspnetForm')
        items = self.br.form.find_control('ctl00$ContentPlaceHolder1$drpState').get_items()
        return items

    def scrape_state_firms(self, state_item):
        self.br.open(self.url)
        self.br.select_form('aspnetForm')
        self.br.form.new_control('hidden', '__EVENTTARGET',   {'value': ''})
        self.br.form.new_control('hidden', '__EVENTARGUMENT', {'value': ''})
        self.br.form.new_control('hidden', '__ASYNCPOST',     {'value': 'true'})
        self.br.form.new_control('hidden', 'ctl00$ScriptManager1', {'value': 'ctl00$ScriptManager1|ctl00$ContentPlaceHolder1$btnSearch'})
        self.br.form.fixup()
        self.br.form['ctl00$ContentPlaceHolder1$drpState'] = [ state_item.name ]

        ctl = self.br.form.find_control('ctl00$ContentPlaceHolder1$btnfrmSearch')
        self.br.form.controls.remove(ctl)

        ctl = self.br.form.find_control('ctl00$ContentPlaceHolder1$btnAccept')
        self.br.form.controls.remove(ctl)

        ctl = self.br.form.find_control('ctl00$ContentPlaceHolder1$btnSearch')
        ctl.disabled = False

        self.br.submit()

        pageno = 2

        while True:
            resp = self.br.response().read()

            it = iter(resp.split('|'))
            kv = dict(zip(it, it))

            s = BeautifulSoup(kv['ctl00_ContentPlaceHolder1_pnlgrdSearchResult'])
            r1 = re.compile(r'^frmFirmDetails\.aspx\?FirmID=([A-Z0-9-]+)$')
            r2 = re.compile(r'hpFirmName$')
            x = {'href': r1, 'id': r2}

            for a in s.findAll('a', attrs=x):
                print 'firm name: ', a.text
                print 'firm url: ', urlparse.urljoin(self.br.geturl(), a['href'])
                print 

            # Find next page number link
            a = s.find('a', text='%d' % pageno)
            if not a:
                break

            pageno += 1

            # New __VIEWSTATE value
            view_state = kv['__VIEWSTATE'] 

            # Extract new __EVENTTARGET value from next page link
            r = re.compile(r"__doPostBack\('([^']+)")
            m = re.search(r, a['href'])
            event_target = m.group(1)

            # Regenerate form for next page
            form = s.find('form', id='aspnetForm').prettify()
            html = form.encode('utf8')
            resp = mechanize.make_response(html, [("Content-Type", "text/html")],
                                           self.br.geturl(), 200, "OK")

            self.br.set_response(resp)
            self.br.select_form('aspnetForm')
            self.br.form.set_all_readonly(False)
            self.br.form['__EVENTTARGET'] = event_target
            self.br.form['__VIEWSTATE'] = view_state
            self.br.form['ctl00$ContentPlaceHolder1$drpState'] = [ state_item.name ]
            self.br.form.new_control('hidden', '__ASYNCPOST',     {'value': 'true'})
            self.br.form.new_control('hidden', 'ctl00$ScriptManager1', {'value': 'ctl00$ContentPlaceHolder1$pnlgrdSearchResult|'+event_target})
            self.br.form.fixup()

            ctl = self.br.form.find_control('ctl00$ContentPlaceHolder1$btnfrmSearch')
            self.br.form.controls.remove(ctl)

            ctl = self.br.form.find_control('ctl00$ContentPlaceHolder1$btnAccept')
            self.br.form.controls.remove(ctl)

            ctl = self.br.form.find_control('ctl00$ContentPlaceHolder1$btnSearch')
            self.br.form.controls.remove(ctl)

            self.br.submit()

    def scrape(self):
        '''
        First we get a list of the states listed in the form select option
        ctl00$ContentPlaceHolder1$drpState

        Then we iterate through each state and submit the form for that state.
        
        For each state form submission we scrape all of the results via
        scrape_firm_page() handling pagination in the process.
        '''
        state_items = self.get_state_items()
        for state_item in state_items:
            if len(state_item.name) < 1:
                continue

            print 'Scraping firms for %s' % state_item.attrs['label']
            self.scrape_state_firms(state_item)

if __name__ == '__main__':
    scraper = ArchitectFinderScraper()
    scraper.scrape()

