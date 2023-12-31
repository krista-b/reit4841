from IPython import embed
import pandas as pd
from os import walk
import logging
import argparse
import functools

cat = {"OriginalQuery": "original_query",
    "QueriesFromWordSwapNeighboringCharacterSwap": "misspelling",
    "QueriesFromWordSwapRandomCharacterSubstitution": "misspelling",
    "QueriesFromWordSwapQWERTY": "misspelling",
    "QueriesFromnaturality_by_removing_stop_words": "naturality",
    "QueriesFromsummarization_with_t5-base_from_description_to_title": "naturality",
    "QueriesFromsummarization_with_t5-large": "naturality",
    "QueriesFromWordInnerSwapRandom": "ordering",
    "QueriesFromback_translation_pivot_language_de": "paraphrase",
    "QueriesFromramsrigouthamg/t5_paraphraser": "paraphrase",
    "QueriesFromt5_uqv_paraphraser": "paraphrase",
    "QueriesFromWordSwapEmbedding": "synonym",
    "QueriesFromWordSwapMaskedLM": "synonym",
    "QueriesFromWordSwapWordNet": "synonym",
    }

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
    # parser.add_argument("--task", default=None, type=str, required=True,
    #                     help="The task to generate weak supervision for (e.g. msmarco-passage/train, car/v1.5/train/fold0).")
    parser.add_argument("--output_dir", default=None, type=str, required=True,
                        help="the folder to output weak supervision")

    args = parser.parse_args()
    path = args.output_dir
    csv_file = "{}/motivation_table_{}.csv"

    task = "msmarco-passage-trec-dl"     
    df = pd.read_csv("{}/query_rewriting_irds:msmarco-passage-trec-dl-2019-judged_model_BM25+BERT_per_query.csv".format(path))
    df['decrease_percentage'] = df['decrease_percentage'] * 100        
    df["name_x"] = df.apply(lambda r: r['name_x'].split("QueriesFrom")[-1], axis=1)

    df_variations = pd.read_csv("{}/variations_trec2019_labeled.csv".format(path))
    df_both = df.merge(df_variations[['q_id', 'method', 'original_query', 'variation']], left_on=["qid","name_x"], right_on=["q_id", "method"])
    df_both = df_both[df_both['measure']=='ndcg_cut_10']
    df_both[df_both['valid']].sort_values(["name_x", "decrease"]).to_csv(csv_file.format(path, task), sep='\t', index=False)

    embed()
    
    task = "antique"
    df = pd.read_csv("{}/query_rewriting_irds:antique-train-split200-valid_model_BM25+BERT_per_query.csv".format(path))
    df['decrease_percentage'] = df['decrease_percentage'] * 100        
    df["name_x"] = df.apply(lambda r: r['name_x'].split("QueriesFrom")[-1], axis=1)

    df_variations = pd.read_csv("{}/variations_antique_labeled.csv".format(path))
    df_both = df.merge(df_variations[['q_id', 'method', 'original_query', 'variation']], left_on=["qid","name_x"], right_on=["q_id", "method"])
    df_both = df_both[df_both['measure']=='ndcg_cut_10']
    df_both[df_both['valid']].sort_values(["name_x", "decrease"]).to_csv(csv_file.format(path, task), sep='\t', index=False)

    embed()

    task = "dl-typo"
    df = pd.read_csv("{}/query_rewriting_dl-typo_model_BM25+BERT_per_query.csv".format(path))
    df['decrease_percentage'] = df['decrease_percentage'] * 100        
    df["name_x"] = df.apply(lambda r: r['name_x'].split("QueriesFrom")[-1], axis=1)

    df_variations = pd.read_csv("{}/variations_dl-typo_edited_labeled.csv".format(path))
    df_both = df.merge(df_variations[['q_id', 'method', 'original_query', 'variation']], left_on=["qid","name_x"], right_on=["q_id", "method"])
    df_both = df_both[df_both['measure']=='ndcg_cut_10']
    df_both[df_both['valid']].sort_values(["name_x", "decrease"]).to_csv(csv_file.format(path, task), sep='\t', index=False)

if __name__ == "__main__":
    main()
