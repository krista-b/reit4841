from IPython import embed
import pandas as pd
from os import walk
import logging
import argparse
import functools

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
                        help="The task to generate generate table")
    parser.add_argument("--path", default=None, type=str, required=True,
                        help="The folder where data exists")
    args = parser.parse_args()
    path = args.path
    task = args.task
    metric = 'ndcg_cut_10'
    p_val = ' p-value'

    _, _, filenames = next(walk(path))
    dfs = []
    for f in filenames:
        if 'query_fusion' in f and task in f:
           df = pd.read_csv(path+f)
           df["variation_method"] = df.apply(lambda r: r['name'].split("+")[-1] if 'CombSum' in r['name'] or 'RRF' in r['name'] else 'OriginalQuery', axis=1)
           baseline_v = df[df["variation_method"] == 'OriginalQuery'][metric].values[0]
        #    df[metric] = df.apply(lambda r, metric=metric, v=baseline_v: 
        #         round(r[metric], 4) if r['variation_method']=='OriginalQuery' else str(round(((r[metric]-v)/v) * 100, 2)) + "%", axis=1)
           df[metric] = df.apply(lambda r, metric=metric, v=baseline_v: round(r[metric], 4), axis=1)
           df[metric + p_val] = df.apply(lambda r, metric=metric: r[metric + p_val] < 0.05,axis=1)
           model_name = f.split("model_")[-1].split(".csv")[0]
           df = df.rename(columns = {metric : "{}_".format(metric) + model_name,
                                     metric + p_val: "p_"+ model_name})
           df = df.set_index('variation_method')
           dfs.append(df[["{}_".format(metric) + model_name, "p_"+ model_name]])
    df_all = functools.reduce(lambda df1, df2: df1.join(df2), dfs)    
    # embed()
    df_all = df_all[["{}_BM25".format(metric), "p_BM25", #"{}_BM25+docT5query".format(metric), "p_BM25+docT5query",
                "{}_BM25+RM3".format(metric), "p_BM25+RM3",
                "{}_BM25+KNRM".format(metric), "p_BM25+KNRM",
                "{}_msmarco.convknrm.seed42.tar.gz".format(metric), "p_msmarco.convknrm.seed42.tar.gz",
                "{}_msmarco.epic.seed42.tar.gz".format(metric), "p_msmarco.epic.seed42.tar.gz",
                "{}_BM25+BERT".format(metric), "p_BM25+BERT",
                 "{}_BM25+T5".format(metric), "p_BM25+T5"]]    
    df_all.round(4).to_csv("{}fusion_table_{}.csv".format(path, task), sep='\t')    

if __name__ == "__main__":
    main()


##UPDATE