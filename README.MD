### Download PDF by pmid

[github](https://github.com/decouples/pubmed_download)

- install

```shell
pip install pubmed_download
```

example:
```python
# -*- encoding:utf-8 -*-
from pubmed_download import DownloadPdf


p_list = ['29632648',
          '22640600',
          '25898960',
          '27780853']

download_path = r"D:/data"
DownloadPdf(download_path, p_list).run()

# pdf files will store in D:/data/{pmid}.pdf
```
