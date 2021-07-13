"""Grobid Client.

This version uses the standard ProcessPoolExecutor for parallelizing the
concurrent calls to the GROBID services.  Given the limits of
ThreadPoolExecutor (the legendary GIL, input stored in memory, blocking
Executor.map until the whole input is acquired), ProcessPoolExecutor works with
batches of PDF of a size indicated in the config.json file (default is 1000
entries). We are moving from first batch to the second one only when the first
is entirely processed - which means it is slightly sub-optimal, but should
scale better. Working without batch would mean acquiring a list of millions of
files in directories and would require something scalable too (e.g. done in a
separate thread), which is not implemented for the moment and possibly not
implementable in Python as long it uses the GIL.
"""
import os
import io
import json
import argparse
import time
import concurrent.futures
import ntpath
import requests
import pathlib

from .client import ApiClient


class GrobidClient(ApiClient):
    def __init__(self, config_path="./config.json", grobid_server='l8', grobid_port='8280', batch_size=10, sleep_time=5,coordinates=['persName', 'figure', 'ref', 'biblStruct', 'formula']):
        """
        如果配置文件存在，加载配置文件，如果不存在，加载给定的配置信息
        """
        self.config = None
        if config_path and os.path.exists(config_path):
            print(f"配置文件存在，加载配置文件")
            self._load_config(config_path)
        else:
            self.config = {'grobid_server': grobid_server, 'grobid_port': grobid_port, 'batch_size': batch_size, 'sleep_time': sleep_time, 'coordinates': coordinates}

    def _load_config(self, path="./config.json"):
        """加载grobid的配置，json文件
        """
        config_json = open(path).read()
        self.config = json.loads(config_json)

        # test if the server is up and running...
        the_url = "http://" + self.config["grobid_server"]
        if len(self.config["grobid_port"]) > 0:
            the_url += ":" + self.config["grobid_port"]
        the_url += "/api/isalive"
        try:
            # 检测下isalive端口，判断是否运行中
            r = requests.get(the_url)
        except:
            print("GROBID服务似乎没有启动, 连接失败，请检查")
            exit(1)

        status = r.status_code

        if status != 200:
            print("GROBID没有启动和运行，返回状态码: " + str(status))
        else:
            print("GROBID服务正在运行种")

    def _output_file_name(self, pdf_file, input_path, output):
        """
        组装出输出tei文件的名字和路径
        """
        if output is not None:
            if input_path == pdf_file:
                # 说明输入是单个pdf文件，那么我们获取pdf的文件名字，需要用另一种方式
                pdf_file_name = os.path.basename(pdf_file)
            else:
                pdf_file_name = str(os.path.relpath(os.path.abspath(pdf_file), input_path))
            filename = os.path.join(
                output, os.path.splitext(pdf_file_name)[0] + ".tei.xml"
            )
        else:
            pdf_file_name = ntpath.basename(pdf_file)
            filename = os.path.join(
                ntpath.dirname(pdf_file),
                os.path.splitext(pdf_file_name)[0] + ".tei.xml",
            )

        return filename

    def process(
        self,
        service,
        input_path,
        output=None,
        n=10,
        generateIDs=False,
        consolidate_header=True,
        consolidate_citations=False,
        include_raw_citations=False,
        include_raw_affiliations=False,
        teiCoordinates=False,
        force=True,
        verbose=False,
    ):
        """
        如果input_path给定的是一个文件，或是一个目录
        """
        # 弃用batch_size，没啥用
        batch_size_pdf = self.config["batch_size"]
        pdf_files = []
        if os.path.isdir(input_path):
            for (dirpath, dirnames, filenames) in os.walk(input_path):
                for filename in filenames:
                    if filename.endswith(".pdf") or filename.endswith(".PDF"):
                        if verbose:
                            try:
                                print(filename)
                            except Exception:
                                # may happen on linux see https://stackoverflow.com/questions/27366479/python-3-os-walk-file-paths-unicodeencodeerror-utf-8-codec-cant-encode-s
                                pass
                        pdf_files.append(os.sep.join([dirpath, filename]))
        else:
            if os.path.exists(input_path):
                pdf_files = [input_path]
            else:
                print(f"给定的pdf文件不存在{input_path}")
        # last batch
        if len(pdf_files) > 0:
            self.process_batch(
                service,
                pdf_files,
                input_path,
                output,
                n,
                generateIDs,
                consolidate_header,
                consolidate_citations,
                include_raw_citations,
                include_raw_affiliations,
                teiCoordinates,
                force,
                verbose,
            )
            print(f"pdf处理完成")
        else:
            print(f"未发现任何pdf文件，请检查路径")

    def process_batch(
        self,
        service,
        pdf_files,
        input_path,
        output,
        n,
        generateIDs,
        consolidate_header,
        consolidate_citations,
        include_raw_citations,
        include_raw_affiliations,
        teiCoordinates,
        force,
        verbose=False,
    ):
        if verbose:
            print(len(pdf_files), "PDF files to process in current batch")

        # with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        with concurrent.futures.ProcessPoolExecutor(max_workers=n) as executor:
            results = []
            for pdf_file in pdf_files:
                # filename是输出文件的名字，检测输出的TEI文件是否存在
                filename = self._output_file_name(pdf_file, input_path, output)
                if not force and os.path.isfile(filename):
                    print(filename, "already exist, skipping... (use --force to reprocess pdf input files)")
                    continue

                r = executor.submit(
                    self.process_pdf,
                    service,
                    pdf_file,
                    generateIDs,
                    consolidate_header,
                    consolidate_citations,
                    include_raw_citations,
                    include_raw_affiliations,
                    teiCoordinates,
                )
                results.append(r)

        for r in concurrent.futures.as_completed(results):
            pdf_file, status, text = r.result()
            # filename是输出文件的TEI名字
            filename = self._output_file_name(pdf_file, input_path, output)
            if text is None:
                print("处理", pdf_file, "时发生错误，错误状态: ", str(status))
            else:
                # writing TEI file
                try:
                    pathlib.Path(os.path.dirname(filename)).mkdir(parents=True, exist_ok=True)
                    with open(filename,'w',encoding='utf8') as tei_file:
                        tei_file.write(text)
                        print(f"处理完成pdf文件{pdf_file}，生成的TEI文件{filename}")
                except OSError:
                   print("Writing resulting TEI XML file", filename, "failed")

    def process_pdf(
        self,
        service,
        pdf_file,
        generateIDs,
        consolidate_header,
        consolidate_citations,
        include_raw_citations,
        include_raw_affiliations,
        teiCoordinates,
    ):

        files = {
            "input": (
                pdf_file,
                open(pdf_file, "rb"),
                "application/pdf",
                {"Expires": "0"},
            )
        }

        the_url = "http://" + self.config["grobid_server"]
        if len(self.config["grobid_port"]) > 0:
            the_url += ":" + self.config["grobid_port"]
        the_url += "/api/" + service

        # set the GROBID parameters
        the_data = {}
        if generateIDs:
            the_data["generateIDs"] = "1"
        if consolidate_header:
            the_data["consolidateHeader"] = "1"
        if consolidate_citations:
            the_data["consolidateCitations"] = "1"
        if include_raw_citations:
            the_data["includeRawCitations"] = "1"
        if include_raw_affiliations:
            the_data["includeRawAffiliations"] = "1"
        if teiCoordinates:
            the_data["teiCoordinates"] = self.config["coordinates"]

        res, status = self.post(
            url=the_url, files=files, data=the_data, headers={"Accept": "text/plain"}
        )

        if status == 503:
            time.sleep(self.config["sleep_time"])
            return self.process_pdf(
                service,
                pdf_file,
                generateIDs,
                consolidate_header,
                consolidate_citations,
                include_raw_citations,
                include_raw_affiliations,
                teiCoordinates,
            )

        return (pdf_file, status, res.text)


def main():
    valid_services = [
        "processFulltextDocument",
        "processHeaderDocument",
        "processReferences",
    ]

    parser = argparse.ArgumentParser(description="Client for GROBID services")
    parser.add_argument(
        "service",
        help="选择使用grobid的哪个服务 [processFulltextDocument, processHeaderDocument, processReferences]",
    )
    parser.add_argument(
        "--input", default=None, help="处理pdf的文件的路径，递归查找并处理的"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出目录，可选，保存解析后的pdf的TEI文件的路径",
    )
    parser.add_argument(
        "--config",
        default="./config.json",
        help="配置文件，加载客户端的配置 ./config.json",
    )
    parser.add_argument("--n", default=10, help="并发，默认使用多少并发同时处理pdf，即同时建立多少个连接")
    parser.add_argument(
        "--generateIDs",
        action="store_true",
        help="生成随机的 xml:id to textual XML elements of the result files",
    )
    parser.add_argument(
        "--consolidate_header",
        action="store_true",
        help="call GROBID with consolidation of the metadata extracted from the header",
    )
    parser.add_argument(
        "--consolidate_citations",
        action="store_true",
        help="call GROBID with consolidation of the extracted bibliographical references",
    )
    parser.add_argument(
        "--include_raw_citations",
        action="store_true",
        help="call GROBID requesting the extraction of raw citations",
    )
    parser.add_argument(
        "--include_raw_affiliations",
        action="store_true",
        help="GROBID提取原始的机构",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="重新处理pdf文件，即使tei文件已经存在",
    )
    parser.add_argument(
        "--teiCoordinates",
        action="store_true",
        help="为提取的元素附加坐标，即(bounding boxes)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印verbose信息",
    )

    args = parser.parse_args()

    input_path = args.input
    config_path = args.config
    output_path = args.output

    if args.n is not None:
        try:
            n = int(args.n)
        except ValueError:
            print("Invalid concurrency parameter n:", n, ", n = 10 will be used by default")
            pass

    # if output path does not exist, we create it
    if output_path is not None and not os.path.isdir(output_path):
        try:
            print("output directory does not exist but will be created:", output_path)
            os.makedirs(output_path)
        except OSError:
            print("Creation of the directory", output_path, "failed")
        else:
            print("Successfully created the directory", output_path)

    service = args.service
    generateIDs = args.generateIDs
    consolidate_header = args.consolidate_header
    consolidate_citations = args.consolidate_citations
    include_raw_citations = args.include_raw_citations
    include_raw_affiliations = args.include_raw_affiliations
    force = args.force
    teiCoordinates = args.teiCoordinates
    verbose = args.verbose

    if service is None or not service in valid_services:
        print("Missing or invalid service, must be one of", valid_services)
        exit(1)

    client = GrobidClient(config_path=config_path)

    start_time = time.time()

    client.process(
        service,
        input_path,
        output=output_path,
        n=n,
        generateIDs=generateIDs,
        consolidate_header=consolidate_header,
        consolidate_citations=consolidate_citations,
        include_raw_citations=include_raw_citations,
        include_raw_affiliations=include_raw_affiliations,
        teiCoordinates=teiCoordinates,
        force=force,
        verbose=verbose,
    )

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))

if __name__ == "__main__":
    main()
