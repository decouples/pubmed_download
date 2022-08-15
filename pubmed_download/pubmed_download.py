# -*- encoding:utf-8 -*-
"""
@author：lin.li
@filename：pubmed_download.py
@time：2022/8/6  22:41
@file description:pubmed_download
"""
import traceback
import pandas as pd
import requests
import os
import PyPDF2
import urllib.request as ub
from bs4 import BeautifulSoup
from .pubmed_mapper import Article
import logging


logger = logging.getLogger('pubmed')
logger.propagate = False
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
formatter = logging.Formatter('[{asctime}] [{name:^5}] [{levelname:^7}] [{lineno:^4}] [{message}]',
                              datefmt='%Y-%m-%d %H:%M:%S', style='{',)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class DownloadPdf:
    """
    给定pmid列表和下载路径，下载对应的pdf文件

    失败的文件写在csv文件中
    """

    def __init__(self, store_path, pmid_list):
        self.store_path = store_path
        self.logger = logger
        self.pmid_list = pmid_list
        self.failed_list = list()

    def download(self, pmid, url):
        """真实下载任务函数

        根据所给pdf下载，根据pmid命名pdf，保存到指定文件夹

        如果url请求失败或者下载的不是pdf删除下载的文件，并返回False
        """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0',
                   'Upgrade-Insecure-Requests': '1',
                   'Cookie': '__cfduid=d9b6123514d7ca2db292dca147121a9041616482481'
                   }
        try:
            response = requests.get(url, stream=True, headers=headers, timeout=60)
            if response.status_code != 200:
                return False
            filename = self.store_path + '/' + os.path.basename(str(pmid)) + '.pdf'
            self.logger.info(f"{pmid} {url}")
            with open(filename, 'wb') as file:
                for data in response.iter_content():
                    file.write(data)
            try:
                with open(filename, 'rb') as f:
                    PyPDF2.PdfFileReader(f)
            except ValueError:
                return True
            except Exception as e:
                self.logger.error(f"{pmid}, download pdf error, {e}")
                os.remove(filename)
                return False
        except Exception as e:
            self.logger.error(f"{pmid}, cannot download, {e}")
            return False
        return True

    def check_downloaded(self, pmid):
        """check pdf exists"""
        pdf_path = os.path.join(self.store_path, f"{pmid}.pdf")
        if os.path.exists(pdf_path) and os.path.isfile(pdf_path):
            return True
        return False

    def run(self):
        """这里做主要的下载工作"""
        self.logger.info("start download.....")
        for pmid in self.pmid_list:
            # time.sleep(3)
            self.logger.info(f"start download {pmid}, {self.pmid_list.index(pmid)}/{len(self.pmid_list)}")
            # 该批次下载过的不再下载
            if self.check_downloaded(pmid):
                self.logger.info(f"file already exist:{pmid}")
                self.failed_list.append(pmid)
                continue
            try:
                article = Article.parse_pmid(pmid)
            except Exception as e:
                self.logger.error(f"parse pmid failed: {pmid}, reason: {traceback.print_exc()}")
                self.failed_list.append(pmid)
                continue
            ids_dict = dict()
            [ids_dict.update({k.id_type: k.id_value}) for k in article.ids]
            doi = ids_dict.get('doi', None)
            pii = ids_dict.get('pii', None)
            pmc = ids_dict.get('pmc', None)
            if doi and self.search_by_doi(pmid, doi.strip()):
                continue
            if pii and self.search_by_pii(pmid, pii.strip()):
                continue
            if pmc and self.search_by_pmc(pmid, pmc.strip()):
                continue
            self.logger.info(f"download failed: {pmid}")
            self.failed_list.append(pmid)
        result_csv = os.path.join(os.path.dirname(self.store_path), "failed_list.csv")
        df = pd.DataFrame(self.failed_list, columns=['pmid'])
        df.to_csv(result_csv, sep='\t', index=False)
        self.logger.info(f"download file done:{len(self.pmid_list) - len(self.failed_list)}/{len(self.pmid_list)}")
        return list(set(self.pmid_list) - set(self.failed_list))

    def search_by_doi(self, pmid, doi):
        """这里使用文章的doi进行文章下载"""
        self.logger.info(f"search by doi: {pmid}, {doi}")
        download_status = False
        temp_url = 'https://sci-hub.ren/' + doi
        opener = ub.build_opener()
        opener.addheaders = [
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0',
             'Upgrade-Insecure-Requests': 1}]
        ub.install_opener(opener)
        try:
            content = ub.urlopen(temp_url).read().decode('utf-8')
            soup = BeautifulSoup(content, 'html.parser')
            pdf_element = soup.find('iframe', id='pdf')
            if pdf_element is not None:
                pdf_url = pdf_element.attrs['src']
                if 'https:' not in pdf_url:
                    pdf_url = 'https:' + pdf_url
                self.logger.info(f"search sci_hub by doi:{pdf_url}")
                download_status = self.download(pmid, pdf_url)
        except Exception as e:
            self.logger.error(f"search sci-hub by doi error: {traceback.print_exc()}")

        candidate_url_list = [
            f"https://sci-hub.wf/{doi}",
            f'https://sci/bban/top/{doi}.pdf#view=FitH',
            f"https://www.spandidos-publications.com/{doi}/download",
            f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
            f"https://jeccr.biomedcentral.com/track/pdf/{doi}",
            f"https://www.frontiersin.org/articles/{doi}/pdf",
            f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable",
            f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
            f"https://www.tandfonline.com/doi/pdf/{doi}?needAccess=true",
            f"https://immunityageing.biomedcentral.com/track/pdf/{doi}",
            f"https://pubs.acs.org/doi/pdf/{doi}",
            f"https://journals.sagepub.com/doi/pdf/{doi}",
            f"https://www.futuremedicine.com/doi/epub/{doi}"
        ]
        for url in candidate_url_list:
            if not download_status:
                self.logger.info(f"try by doi: {url}")
                self.download(pmid, url.strip())
            else:
                break
        self.logger.info(f"download by doi:{download_status}")
        return download_status

    def search_by_pii(self, pmid, pii):
        """这里使用pii下载文章"""
        self.logger.info(f"search by pii, {pmid}, {pii}...")
        download_status = False
        candidate_url_list = [
            f'https://www.jto.org/action/showPdf?pii={pii}',
            f"https://www.jto.org/article/{pii}/pdf",
            f"https://www.oncotarget.com/article/{pii}/pdf/"
        ]
        for url in candidate_url_list:
            if not download_status:
                self.logger.info(f'try by pii: {url}')
                download_status = self.download(pmid, url)
            else:
                break
        self.logger.info(f"download by pii: {download_status}")
        return download_status

    def search_by_pmc(self, pmid, pmc):
        """根据pmc尝试去对应网站下载pdf"""
        download_status = False
        try:
            temp_url = f'https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc}'
            content = ub.urlopen(temp_url).read().decode('utf-8')
            soup = BeautifulSoup(content, 'html.parser')
            pdf_url = 'https://www.ncbi.nlm.nih.gov' + \
                      soup.find('link', type='application/pdf').attrs['href']
            self.logger.info(f"try by pmc {pdf_url}")
            download_status = self.download(pmid, pdf_url)
        except Exception as e:
            self.logger.error(f"{pmid}, concat pmc-url error-->, {e}")
        candidate_url_list = [
            f"http://europepmc.org/articles/{pmc.lower()}?pdf=render"
        ]
        for url in candidate_url_list:
            if not download_status:
                self.logger.info(f"try by pmc: {url}")
                download_status = self.download(pmid, url)
            else:
                break
        self.logger.info(f"download by pmc: {download_status}")
        return download_status
