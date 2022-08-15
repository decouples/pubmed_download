# -*- coding: utf-8 -*-
"""
PubMed Mapper: A Python library that map PubMed XML to Python object
"""
import re
from datetime import date
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from lxml import etree


MONTHS = {
    'Jan': 1, 'Feb': 2, 'Mar': 3,
    'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9,
    'Sept': 9, 'Oct': 10, 'Nov': 11,
    'Dec': 12,
    'January': 1, 'February': 2, 'March': 3,
    'April': 4,  # 'May': 5,
    'June': 6, 'July': 7, 'August': 8, 'September': 9,
    'October': 10, 'November': 11, 'Novembre': 11, 'December': 12
}

SEASONS = {
    'Spring': 4, 'Summer': 7,
    'Fall': 10, 'Autumn': 10, 'Winter': 1
}


class PubmedMapperError(Exception):
    """PubmedMapper Error"""
    pass


def extract_first(data):
    if not (isinstance(data, list) and (len(data) >= 1)):
        return None
    return data[0]


def get_inner_html(element, strip=True):
    texts = []
    if element is None:
        return ""
    if element.text:
        texts.append(element.text)
    for child in element.getchildren():
        if child.text:
            texts.append(child.text)
        if child.tail:
            texts.append(child.tail)
    if element.tail:
        texts.append(element.tail)
    text = ''.join(texts)
    if strip:
        text = text.strip()
    return text


class ArticleId(object):
    def __init__(self, id_type, id_value):
        self.id_type = id_type
        self.id_value = id_value

    def __repr__(self):
        return '%s: %s' % (self.id_type, self.id_value)

    def to_dict(self):
        return {
            'id_type': self.id_type,
            'id_value': self.id_value
        }

    @classmethod
    def parse_element(cls, element):
        return cls(
            id_type=element.get('IdType'),
            id_value=element.text
        )


class Mesh(object):
    def __init__(self, id_type, id_value):
        self.id_type = id_type
        self.id_value = id_value

    def __repr__(self):
        return '%s: %s' % (self.id_type, self.id_value)

    def to_dict(self):
        return {
            'id_type': self.id_type,
            'id_value': self.id_value
        }

    @classmethod
    def parse_element(cls, element):
        return cls(
            id_type=element.get('UI'),
            id_value=element.text
        )


class Publication(object):
    def __init__(self, id_type, id_value):
        self.id_type = id_type
        self.id_value = id_value
    
    def __repr__(self):
        return '%s: %s' % (self.id_type, self.id_value)
    
    def to_dict(self):
        return {
            'id_type': self.id_type,
            'id_value': self.id_value
        }
    
    @classmethod
    def parse_element(cls, element):
        return cls(
            id_type=element.get('UI'),
            id_value=element.text
        )
    

class PubdateDefaults(object):
    """default year, month, day"""
    default_year = 1
    default_month = 1
    default_day = 1


class PubdateParserYearMonthDay(PubdateDefaults):
    """年份、月份、日期都有"""
    def __call__(self, element):
        year_text = extract_first(element.xpath('./Year/text()'))
        month_text = extract_first(element.xpath('./Month/text()'))
        day_text = extract_first(element.xpath('./Day/text()'))
        if not (year_text and month_text and day_text):
            return None
        if month_text.isdigit():
            month = int(month_text)
        else:
            month = MONTHS[month_text.capitalize()]
        return date(
            year=int(year_text),
            month=month,
            day=int(day_text)
        )


class PubdateParserYearMonth(PubdateDefaults):
    """只有年份、月份"""
    def __call__(self, element):
        year_text = extract_first(element.xpath('./Year/text()'))
        month_text = extract_first(element.xpath('./Month/text()'))
        if not (year_text and month_text):
            return None
        if month_text.isdigit():
            month = int(month_text)
        else:
            month = MONTHS[month_text.capitalize()]
        return date(year=int(year_text), month=month, day=self.default_day)


class PubdateParserYearSeason(PubdateDefaults):
    """只有年份、季节"""
    def __call__(self, element):
        year_text = extract_first(element.xpath('./Year/text()'))
        season_text = extract_first(element.xpath('./Season/text()'))
        if not (year_text and season_text):
            return None
        year = int(year_text)
        month = SEASONS[season_text]
        return date(year=year, month=month, day=self.default_day)


class PubdateParserYearOnly(PubdateDefaults):
    """只有年份"""
    def __call__(self, element):
        year_text = extract_first(element.xpath('./Year/text()'))
        if not year_text:
            return None
        return date(
            year=int(year_text),
            month=self.default_month,
            day=self.default_day
        )


class PubdateParserMedlineDateYearOnly(PubdateDefaults):
    """MedlineDate字段只有年份"""
    pattern = re.compile(r'^(?P<year>\d{4}$)')

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        return date(
            year=year,
            month=self.default_month,
            day=self.default_day
        )


class PubdateParserMedlineDateMonthRange(PubdateDefaults):
    """MedlineDate字段同一年月份有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3,})(.*)-(.*)[a-zA-Z]{3}$'
    )
    pattern2 = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3,})(.*)/(.*)[a-zA-Z]{3}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            match = self.pattern2.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month_txt = match.groupdict()['month_text'].capitalize()
        if month_txt in MONTHS.keys():
            month = MONTHS[month_txt]
        else:
            return None
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


class PubdateParserMedlineDateDayRange(PubdateDefaults):
    """MedlineDate字段同一年月份有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3,}) (?P<day>\d{1,2})-\d{1,2}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month_txt = match.groupdict()['month_text'].capitalize()
        if month_txt in MONTHS.keys():
            month = MONTHS[month_txt]
        else:
            return None
        day = int(match.groupdict()['day'])
        return date(
            year=year,
            month=month,
            day=day
        )


class PubdateParserMedlineDateFullMonthYear(PubdateDefaults):
    """MedlineDate字段年 月份为全拼"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3,})$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month_txt = match.groupdict()['month_text'].capitalize()
        if month_txt in MONTHS.keys():
            month = MONTHS[match.groupdict()['month_text'].capitalize()]
        else:
            return None
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


class PubdateParserMedlineDateMonthRangeCrossYear(PubdateDefaults):
    """MedlineDate字段不同一年月份有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3,})-\d{4} [a-zA-Z]{3}$'
    )
    pattern2 = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>\d{1,2})-\d{1,2}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            match = self.pattern2.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month = int(match.groupdict()['month_text'].capitalize())
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


class PubdateParserMedlineDateRangeYear(PubdateDefaults):
    """MedlineDate字段年份区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4})-\d{4}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        return date(
            year=year,
            month=self.default_month,
            day=self.default_day
        )


class PubdateParserMedlineDateMonthDayRange(PubdateDefaults):
    """MedlineDate字段在同一年月份、日期有区间"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3,}) (?P<day>\d{1,2})-[a-zA-Z]{3} \d{1,2}$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month = MONTHS[match.groupdict()['month_text'].capitalize()]
        day = int(match.groupdict()['day'])
        return date(
            year=year,
            month=month,
            day=day
        )


class PubdateParserMedlineDateMonthDay(PubdateDefaults):
    """MedlineDate字段在同一年月日"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<month_text>[a-zA-Z]{3,}) (?P<day>\d{1,2})$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        month = MONTHS[match.groupdict()['month_text'].capitalize()]
        day = int(match.groupdict()['day'])
        return date(
            year=year,
            month=month,
            day=day
        )


class PubdateParserMedlineDateYearRangeWithSeason(PubdateDefaults):
    """eg, 1976-1977 Winter"""
    pattern = re.compile(
        r'^(?P<year>\d{4})-\d{4} (?P<season_text>[a-zA-Z]+)$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        season_text = match.groupdict()['season_text'].capitalize()
        if season_text in SEASONS.keys():
            month = SEASONS[season_text]
        else:
            return None
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


class PubdateParserMedlineDateYearWithSeason(PubdateDefaults):
    """eg, Winter 1976 or 1976 Winter"""
    pattern = re.compile(
        r'^(?P<year>\d{4}) (?P<season_text>[a-zA-Z]+)$'
    )
    pattern2 = re.compile(
        r'^(?P<season_text>[a-zA-Z]+) (?P<year>\d{4})$'
    )
    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            match = self.pattern2.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        season_text = match.groupdict()['season_text'].capitalize()
        if season_text in SEASONS:
            month = SEASONS[season_text]
        else:
            return None
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


class PubdateParserMedlineDateYearSeasonRange(PubdateDefaults):
    """eg, 1977-1978 Fall-Winter"""
    pattern = re.compile(
        r'^(?P<year>\d{4})-\d{4} (?P<season_text>[a-zA-Z]+)-[a-zA-Z]+$'
    )

    def __call__(self, element):
        medline_date_text = extract_first(element.xpath('./MedlineDate/text()'))
        if not medline_date_text:
            return None
        match = self.pattern.search(medline_date_text)
        if not match:
            return None
        year = int(match.groupdict()['year'])
        season_text = match.groupdict()['season_text'].capitalize()
        if season_text in SEASONS:
            month = SEASONS[season_text]
        else:
            return None
        return date(
            year=year,
            month=month,
            day=self.default_day
        )


PUBDATE_PARSERS = [
    PubdateParserYearMonthDay(),
    PubdateParserYearMonth(),
    PubdateParserYearSeason(),
    PubdateParserYearOnly(),
    PubdateParserMedlineDateYearOnly(),
    PubdateParserMedlineDateMonthRange(),
    PubdateParserMedlineDateDayRange(),
    PubdateParserMedlineDateFullMonthYear(),
    PubdateParserMedlineDateMonthRangeCrossYear(),
    PubdateParserMedlineDateRangeYear(),
    PubdateParserMedlineDateMonthDay(),
    PubdateParserMedlineDateMonthDayRange(),
    PubdateParserMedlineDateYearWithSeason(),
    PubdateParserMedlineDateYearRangeWithSeason(),
    PubdateParserMedlineDateYearSeasonRange(),
]


class JournalElementParserMixin(object):
    @staticmethod
    def parse_issn(element):
        return extract_first(element.xpath('./ISSN/text()'))

    @staticmethod
    def parse_issn_type(element):
        issn_element = extract_first(element.xpath('./ISSN'))
        if issn_element is None:
            return None
        return issn_element.get('IssnType')

    @staticmethod
    def parse_title(element):
        return element.xpath('./Title/text()')[0]

    @staticmethod
    def parse_abbr(element):
        return element.xpath('./ISOAbbreviation/text()')[0]


class Journal(JournalElementParserMixin):
    def __init__(self, issn, issn_type, title, abbr):
        self.issn = issn
        self.issn_type = issn_type
        self.title = title
        self.abbr = abbr

    def __repr__(self):
        return self.title

    def to_dict(self):
        return {
            'issn': self.issn,
            'issn_type': self.issn_type,
            'title': self.title,
            'abbr': self.abbr
        }

    @classmethod
    def parse_element(cls, element):
        issn = cls.parse_issn(element)
        issn_type = cls.parse_issn_type(element)
        title = cls.parse_title(element)
        abbr = cls.parse_abbr(element)
        return cls(
            issn=issn, issn_type=issn_type, title=title, abbr=abbr
        )


class Reference(object):
    def __init__(self, citation, ids):
        self.citation = citation
        self.ids = ids

    def __repr__(self):
        return self.citation

    def to_dict(self):
        return {
            'citation': self.citation,
            'ids': [_.to_dict() for _ in self.ids]
        }

    @classmethod
    def parse_element(cls, element):
        """
        parse <Reference></Reference> tag. eg,
        <Reference>
            <Citation>Metabolism. 2009 Jan;58(1):102-8</Citation>
            <ArticleIdList>
                <ArticleId IdType="pubmed">19059537</ArticleId>
            </ArticleIdList>
        </Reference>
        """
        citation = element.xpath('./Citation/text()')[0]
        ids = [
            ArticleId.parse_element(
                article_id_element
            ) for article_id_element in element.xpath(
                './ArticleIdList/ArticleId'
            )
        ]
        return cls(citation=citation, ids=ids)


class AuthorElementParserMixin(object):
    @staticmethod
    def parse_last_name(element):
        return extract_first(element.xpath('./LastName/text()'))

    @staticmethod
    def parse_forename(element):
        return extract_first(element.xpath('./ForeName/text()'))

    @staticmethod
    def parse_initials(element):
        return extract_first(element.xpath('./Initials/text()'))

    @staticmethod
    def parse_affiliation(element):
        return extract_first(element.xpath('./AffiliationInfo/Affiliation/text()'))


class Author(AuthorElementParserMixin):
    def __init__(self, last_name, forename, initials, affiliation):
        """
        Args:
            last_name: 姓
            forename: 名
            initials:
        """
        self.last_name = last_name
        self.forename = forename
        self.initials = initials
        self.affiliation = affiliation

    def __repr__(self):
        return '%s %s %s' % (self.last_name, self.initials, self.forename)

    def to_dict(self):
        return {
            'last_name': self.last_name,
            'forename': self.forename,
            'initials': self.initials,
            'affiliation': self.affiliation
        }

    @classmethod
    def parse_element(cls, element):
        last_name = cls.parse_last_name(element)
        forename = cls.parse_forename(element)
        initials = cls.parse_initials(element)
        affiliation = cls.parse_affiliation(element)
        return cls(
            last_name=last_name,
            forename=forename,
            initials=initials,
            affiliation=affiliation
        )


class ArticleElementParserMixin(object):
    @staticmethod
    def _parse_pmid(element):
        return element.xpath('./MedlineCitation/PMID/text()')[0]

    @staticmethod
    def parse_ids(element):
        return [
            ArticleId.parse_element(
                article_id_element
            ) for article_id_element in element.xpath(
                './PubmedData/ArticleIdList/ArticleId'
            )
        ]

    @staticmethod
    def parse_mesh(element):
        return [
            Mesh.parse_element(mesh_element) for mesh_element in element.xpath(
                './MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName'
            )
        ]
    
    @staticmethod
    def parse_publication(element):
        return [
            Publication.parse_element(pub_element) for pub_element in element.xpath(
                './MedlineCitation/Article/PublicationTypeList/PublicationType'
            )
        ]

    @staticmethod
    def parse_title(element):
        title_element = extract_first(element.xpath(
            './MedlineCitation/Article/ArticleTitle'
        ))
        return get_inner_html(title_element)

    @staticmethod
    def parse_page(element):
        page_element = extract_first(element.xpath(
            './MedlineCitation/Article/Pagination/MedlinePgn'
        ))
        return get_inner_html(page_element)

    @staticmethod
    def parse_language(element):
        page_element = extract_first(element.xpath(
            './MedlineCitation/Article/Language'
        ))
        return get_inner_html(page_element)

    @staticmethod
    def parse_country(element):
        page_element = extract_first(element.xpath(
            './MedlineCitation/MedlineJournalInfo/Country'
        ))
        return get_inner_html(page_element)

    @staticmethod
    def parse_abstract(element):
        paragraphs = []
        for abstract_text_element in element.xpath(
                './MedlineCitation/Article/Abstract/AbstractText'
        ):
            label = abstract_text_element.get('Label', None)
            sub_title = ''
            if label:
                label = label.capitalize()
                sub_title = '%s:' % label
            paragraph = '%s%s' % (sub_title, get_inner_html(abstract_text_element))
            paragraphs.append(paragraph)
        return ''.join(paragraphs)

    @staticmethod
    def parse_keywords(element):
        return element.xpath('./MedlineCitation/KeywordList/Keyword/text()')

    @staticmethod
    def parse_authors(element):
        return [
            Author.parse_element(element) for element in element.xpath(
                './MedlineCitation/Article/AuthorList/Author'
            )
        ]

    @staticmethod
    def parse_journal(element):
        return Journal.parse_element(
            element.xpath('./MedlineCitation/Article/Journal')[0]
        )

    @staticmethod
    def parse_volume(element):
        return extract_first(element.xpath(
            './MedlineCitation/Article/Journal/JournalIssue/Volume/text()'
        ))

    @staticmethod
    def parse_issue(element):
        return extract_first(element.xpath(
            './MedlineCitation/Article/Journal/JournalIssue/Issue/text()'
        ))

    @staticmethod
    def parse_references(element):
        return [
            Reference.parse_element(
                reference_element
            ) for reference_element in element.xpath(
                './PubmedData/ReferenceList/Reference'
            )
        ]

    @staticmethod
    def parse_pubdate(element):
        pubdate_element = element.xpath(
            './MedlineCitation/Article/Journal/JournalIssue/PubDate'
        )[0]
        pubdate = None
        for parser in PUBDATE_PARSERS:
            pubdate = parser(pubdate_element)
            if pubdate:
                break
        if pubdate is None:
            raise PubmedMapperError('日期无法解析，日期格式：%s' % etree.tostring(
                pubdate_element, encoding='utf-8', pretty_print=True
            ))
        return pubdate


class Article(ArticleElementParserMixin):
    def __init__(
            self,
            pmid,
            ids,
            title,
            abstract,
            keywords,
            mesh_headings,
            authors,
            journal,
            publications,
            volume,
            issue,
            references,
            pubdate,
            page,
            language,
            country
    ):
        self.pmid = pmid
        self.ids = ids
        self.title = title
        self.abstract = abstract
        self.keywords = keywords
        self.mesh_headings = mesh_headings
        self.authors = authors
        self.publications = publications
        self.journal = journal
        self.volume = volume
        self.issue = issue
        self.references = references
        self.pubdate = pubdate
        self.page = page
        self.language = language
        self.country = country

    def __repr__(self):
        return self.title

    def to_dict(self):
        return {
            'pmid': self.pmid,
            'ids': [_.to_dict() for _ in self.ids],
            'title': self.title,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'mesh_headings': self.mesh_headings,
            'authors': [author.to_dict() for author in self.authors],
            'publications': self.publications,
            'journal': self.journal.to_dict(),
            'volume': self.volume,
            'issue': self.issue,
            'references': [reference.to_dict() for reference in self.references],
            'pubdate': self.pubdate.strftime('%Y-%m-%d'),
            'page': self.page,
            'language': self.language,
            'country': self.country
        }

    @classmethod
    def parse_element(cls, element):
        pmid = cls._parse_pmid(element)
        ids = cls.parse_ids(element)
        title = cls.parse_title(element)
        abstract = cls.parse_abstract(element)
        keywords = cls.parse_keywords(element)
        mesh_headings = cls.parse_mesh(element)
        authors = cls.parse_authors(element)
        journal = cls.parse_journal(element)
        publications = cls.parse_publication(element)
        volume = cls.parse_volume(element)
        issue = cls.parse_issue(element)
        references = cls.parse_references(element)
        pubdate = cls.parse_pubdate(element)
        page = cls.parse_page(element)
        language = cls.parse_language(element)
        country = cls.parse_country(element)
        return Article(
            pmid=pmid,
            ids=ids,
            title=title,
            abstract=abstract,
            keywords=keywords,
            mesh_headings=mesh_headings,
            authors=authors,
            journal=journal,
            publications=publications,
            volume=volume,
            issue=issue,
            references=references,
            pubdate=pubdate,
            page=page,
            language=language,
            country=country
        )

    @classmethod
    def parse_pmid(cls, pmid):
        url = ('https://eutils.ncbi.nlm.nih.gov'
               '/entrez/eutils/efetch.fcgi?'
               'db=pubmed&id=%s&retmode=xml') % pmid
        try:
            handle = urlopen(url, timeout=60)
        except (URLError, HTTPError) as e:
            print('cannot download %s', pmid)
            print(e)
            return None
        root = etree.parse(handle)
        try:
            element = root.xpath('/PubmedArticleSet/PubmedArticle')[0]
        except Exception as e:
            return None
        return cls.parse_element(element)
