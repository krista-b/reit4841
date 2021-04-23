from IPython import embed
from pyterrier.utils import Utils
from trectools import TrecRun, TrecEval, TrecQrel, fusion

import pyterrier_ance
import pyterrier as pt
if not pt.started():
  pt.init()

import pandas as pd
import ir_datasets
import argparse
import logging
import re
import os
import sys


def main():
    logging_level = logging.INFO
    logging_fmt = "%(asctime)s [%(levelname)s] %(message)s"
    try:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging_level)
        root_handler = root_logger.handlers[0]
        root_handler.setFormatter(logging.Formatter(logging_fmt))
    except IndexError:
        logging.basicConfig(level=logging_level, format=logging_fmt)

    parser = argparse.ArgumentParser()

    # Input and output configs
    parser.add_argument("--task", default=None, type=str, required=True,
                        help="The task to evaluate (e.g. msmarco-passage/train, car/v1.5/train/fold0).")
    parser.add_argument("--variations_file", default=None, type=str, required=True,
                        help="")
    parser.add_argument("--output_dir", default=None, type=str, required=True,
                        help="")
    parser.add_argument("--retrieval_model_name", default="BM25", type=str, required=False, 
                        help="[BM25, ANCE]")
    parser.add_argument("--ance_checkpoint", default="", type=str, required=False, 
                        help="ance_checkpoint from https://github.com/microsoft/ANCE/#results")                      
    args = parser.parse_args()

    query_variations = pd.read_csv(args.variations_file)
    query_variations["query"] = query_variations.apply(lambda r, re=re: re.sub('[\W_]', ' ',  r['original_query'].lower()), axis=1)
    query_variations["variation"] = query_variations.apply(lambda r, re=re: re.sub('[\W_]', ' ',  r['variation'].lower()), axis=1)
    query_variations["variation"] = query_variations.apply(lambda r: r['query'] if r['variation'].strip() == "" else r['variation'], axis=1)
    query_variations['qid'] = query_variations['q_id'].astype(str)

    dataset = pt.datasets.get_dataset(args.task)
    index_path = '{}/{}-index'.format(args.output_dir, args.task.replace('/', '-'))
    if not os.path.isdir(index_path):
        indexer = pt.index.IterDictIndexer(index_path)
        indexref = indexer.index(dataset.get_corpus_iter(), fields=('doc_id', 'text'))
    index = pt.IndexFactory.of(index_path+"/data.properties")

    # bm_25 = 
    if args.retrieval_model_name == "BM25":
        retrieval_model = pt.BatchRetrieve(index, wmodel="BM25")
    elif args.retrieval_model_name == "ANCE":
        index_path_ance = '{}/{}-index-ance'.format(args.output_dir, args.task.replace('/', '-'))
        if not os.path.isdir(index_path_ance):
            indexer = pyterrier_ance.ANCEIndexer(args.ance_checkpoint, index_path_ance)
            indexer.index(dataset.get_corpus_iter())
        retrieval_model = pyterrier_ance.ANCERetrieval(args.ance_checkpoint, index_path_ance, num_results=10000)

    metrics = ['recip_rank', 'map', 'recall_1000']
    runs_by_type = {}
    all_runs = []

    logging.info("Running baseline model.")
    res_retrieval_baseline_model = retrieval_model.transform(query_variations[['query','qid']].drop_duplicates())
    res_retrieval_baseline_model["system"] = "{}_{}".format(args.retrieval_model_name, 'original_query')
    res_retrieval_baseline_model["query"] = res_retrieval_baseline_model['qid']
    res_retrieval_baseline_model['docid'] = res_retrieval_baseline_model['docno']
    res_retrieval_baseline_model.sort_values(["query","score"], inplace=True, ascending=[True,False])
    trec_run_standard_queries = TrecRun()
    trec_run_standard_queries.run_data = res_retrieval_baseline_model

    for method in query_variations['method'].unique():
        logging.info("Running model for queries generated by method {}".format(method))
        query_variation = query_variations[query_variations['method'] == method]
        query_variation['query'] = query_variation['variation']
        method_type = query_variation["transformation_type"].unique()[0]
        res = retrieval_model.transform(query_variation[['query','qid']].drop_duplicates())
        res["system"] = "{}_{}".format(args.retrieval_model_name, method)
        res["query"] = res['qid']
        res['docid'] = res['docno']
        res.sort_values(["query","score"], inplace=True, ascending=[True,False])
        trec_run = TrecRun()
        trec_run.run_data = res

        if method_type not in runs_by_type:
            runs_by_type[method_type] = []
        runs_by_type[method_type].append(trec_run)
        all_runs.append(trec_run)

    logging.info("Applying rank fusion")

    fused_run = fusion.reciprocal_rank_fusion(all_runs + [trec_run_standard_queries])
    fused_df_all = fused_run.run_data
    fused_df_all['qid'] = fused_df_all['query']
    fused_df_all['docno'] = fused_df_all['docid']
    fused_df_all = fused_df_all[["qid", "docid", "docno", "score", "rank"]]    

    fused_by_cat = []
    for cat in runs_by_type.keys():
        logging.info("Applying rank fusion for cat {}".format(cat))
        fused_run = fusion.reciprocal_rank_fusion(runs_by_type[cat] + [trec_run_standard_queries])
        fused_df = fused_run.run_data
        fused_df['qid'] = fused_df['query']
        fused_df['docno'] = fused_df['docid']
        fused_by_cat.append(fused_df)

    logging.info("Running evaluation experiment.")
    final_df = pt.Experiment(
            [res_retrieval_baseline_model, fused_df_all] + fused_by_cat,
            query_variations[['query','qid']].drop_duplicates(),
            dataset.get_qrels(),
            metrics,
            baseline=0,
            names=["{}".format(args.retrieval_model_name), 
            "{}+RRF_ALL".format(args.retrieval_model_name)] + ["{}+RFF_{}".format(args.retrieval_model_name, cat) for cat in runs_by_type.keys()])

    final_df.to_csv("{}/query_fusion_{}_model_{}.csv".format(args.output_dir, args.task.replace("/",'-'), args.retrieval_model_name), index=False)

if __name__ == "__main__":
    main()