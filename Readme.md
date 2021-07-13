# Simple python client for GROBID REST services

这个Python client可以用来通过[GROBID](https://github.com/kermitt2/grobid)服务以高效的并发方式处理指定目录下的一组PDF。它包括一个命令行，用于在文件系统上处理PDF，并将结果写入给定的输出目录，以及一个用于在其他python脚本中导入的库。

## Build and run

你首先需要安装并启动*grobid*服务，最新的稳定版本，见[文档]（http://grobid.readthedocs.io/）。假设gobid将在地址`http://localhost:8070`上运行。你可以通过编辑文件`config.json`来改变服务器地址。

## Requirements

This client has been developed and tested with Python `3.5` and should work with any higher `3.*` versions. It does not require any dependencies beyond the standard python ones.

## 安装

Get the github repo:

```
git clone https://github.com/kermitt2/grobid_client_python
cd grobid_client_python
python setup.py install
```



要开始使用python命令行，没有什么可做的了，请看下一节。

## Usage and options

```
usage: grobid_client [-h] [--input INPUT] [--output OUTPUT]
                        [--config CONFIG] [--n N] [--generateIDs]
                        [--consolidate_header] [--consolidate_citations]
                        [--include_raw_citations] [--include_raw_affiliations]
                        [--force] [--teiCoordinates] [--verbose]
                        service

Client for GROBID services

positional arguments:
  service               one of [processFulltextDocument,
                        processHeaderDocument, processReferences]

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         path to the directory containing PDF to process
  --output OUTPUT       path to the directory where to put the results
                        (optional)
  --config CONFIG       path to the config file, default is ./config.json
  --n N                 concurrency for service usage
  --generateIDs         generate random xml:id to textual XML elements of the
                        result files
  --consolidate_header  call GROBID with consolidation of the metadata
                        extracted from the header
  --consolidate_citations
                        call GROBID with consolidation of the extracted
                        bibliographical references
  --include_raw_citations
                        call GROBID requesting the extraction of raw citations
  --include_raw_affiliations
                        call GROBID requestiong the extraciton of raw
                        affiliations
  --force               force re-processing pdf input files when tei output
                        files already exist
  --teiCoordinates      add the original PDF coordinates (bounding boxes) to
                        the extracted elements
  --verbose             print information about processed files in the console

```

Examples:

> grobid_client --input ~/tmp/in2 --output ~/tmp/out processFulltextDocument

该命令将使用GROBID的 "processFulltextDocument "服务，递归处理输入目录下的所有PDF文件（仅扩展名为".pdf "的文件），并在输出目录下写入生成的XML TEI文件，重复使用不同文件扩展名（".tei.xml"），使用默认的`10`并发。
如果省略了`--output`，产生的XML TEI文件将与PDF一起在`--input`目录下产生。

> grobid_client --input ~/tmp/in2 --output ~/tmp/out --n 20 processHeaderDocument

这个命令将用GROBID的 "processHeaderDocument "服务处理所有存在于输入目录中的PDF文件（仅扩展名为".pdf "的文件），并在输出目录下写入生成的XML TEI文件，重复使用不同文件扩展名（".tei.xml"），使用`20`并发。

默认情况下，如果在输出目录中存在一个现有的`.tei.xml`文件，对应于输入目录中的一个PDF，这个PDF将被跳过，以避免多次重新处理同一个PDF。要强制处理PDF和覆盖现有的TEI文件，请使用参数`--force`。

文件`example.py`给出了一个来自另一个python脚本的使用例子。

## Using the client in your python

Import and call the client as follow:

```
from grobid_client.grobid_client import GrobidClient

client = GrobidClient(config_path="./config.json")
client.process("processFulltextDocument", "/mnt/data/covid/pdfs", n=20)
```

See also `example.py`.

## Benchmarking

Full text processing of __136 PDF__ (total 3443 pages, in average 25 pages per PDF) on Intel Core i7-4790K CPU 4.00GHz, 4 cores (8 threads), 16GB memory, `n` being the concurrency parameter:

| n  | runtime (s)| s/PDF | PDF/s |
|----|------------|-------|-------|
| 1  | 209.0      | 1.54  | 0.65  |
| 2  | 112.0      | 0.82  | 1.21  |
| 3  | 80.4       | 0.59  | 1.69  |
| 5  | 62.9       | 0.46  | 2.16  |
| 8  | 55.7       | 0.41  | 2.44  |
| 10 | 55.3       | 0.40  | 2.45  |

![Runtime Plot](resources/20180928112135.png)

作为补充信息，GROBID对136份PDF的标题进行处理，并且`n=10'，需要3.74秒（比完整的全文处理快15倍，因为只考虑PDF的前两页），36 PDF/s。在类似条件下，书目参考文献的提取和结构化需要26.9秒（5.1 PDF/s）。

## Todo

Benchmarking with many more files (e.g. million PDFs). Also implement existing GROBID services for text input (date, name, affiliation/address, raw bibliographical references, etc.). Better support for parameters.

## License and contact

Distributed under [Apache 2.0 license](http://www.apache.org/licenses/LICENSE-2.0). 

Main author and contact: Patrice Lopez (<patrice.lopez@science-miner.com>)
