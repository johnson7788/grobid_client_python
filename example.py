from grobid_client.grobid_client import GrobidClient

if __name__ == "__main__":
    # 覆盖config.json的配置
    grobid_server = 'l8'
    grobid_port = '8280'
    process_num = 1
    #返回坐标的元素
    coordinates = ['persName', 'figure', 'ref', 'biblStruct', 'formula']
    client = GrobidClient(config_path=None,grobid_server=grobid_server, grobid_port=grobid_port,coordinates=coordinates)
    # client.process(service="processFulltextDocument", input_path="./resources/test", output="./resources/test_out/", n=process_num, consolidate_citations=True, teiCoordinates=True, force=True)
    client.process(service="processFulltextDocument", input_path="/Users/admin/git/grobid_client_python/resources/test/0046d83a-edd6-4631-b57c-755cdcce8b7f.pdf", output="./resources/test_out/", n=process_num, consolidate_citations=True, teiCoordinates=True, force=True)
