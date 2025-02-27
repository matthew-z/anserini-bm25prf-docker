#!/usr/bin/env python3
import json
import numpy as np
import argparse
import multiprocessing
from runner import Runner, Params, Bm25PRFParams, Bm25Params


parser = argparse.ArgumentParser()
parser.add_argument("--json", type=json.loads,
                    required=True, help="the json input")

input_json = parser.parse_args().json

K1_RANGE = np.arange(0.2, 2.0, 0.1)
B_RANGE = np.arange(0.1, 1.0, 0.1)

PRF_K1_RANGE = np.arange(0.2, 2.0, 0.2)
PRF_B_RANGE = np.arange(0.1, 1.0, 0.2)

TERM_WEIGHT_RANGE = [0.1, 0.2, 0.5, 1]
N_TERMS_RANGE = [0, 5, 10, 20, 40]
N_DOCS_RANGE = [5, 10, 20]

# test 
# K1_RANGE = [0.1, 0.5]
# B_RANGE = [0.2, 0.3]

# PRF_K1_RANGE = [0.1, 0.5]
# PRF_B_RANGE = [0.2, 0.3]

# TERM_WEIGHT_RANGE = [0.1,  1]
# N_TERMS_RANGE = [0,  40]
# N_DOCS_RANGE = [5, 40]


INDEX = input_json.get("index", "robust04")
TOPICS = input_json.get("topics","data/topics.dev.txt")
QRELS_DEV = input_json.get("qrels", "data/qrels.dev.txt")
OUTPUT = input_json.get("output_dir", "/tmp")

def get_eval_result(runner):
    return runner()

def bm25_runner(k1, b):
    params = Bm25Params(k1=k1, b=b)
    runner = Runner(INDEX, TOPICS, OUTPUT,
                    model_params=params, eval_method="P.20", qrel_path=QRELS_DEV)
    return runner


def bm25prf_runner(k1, b, k1_prf, b_prf, num_terms, num_docs, weight):
    params = Bm25PRFParams(k1=k1, b=b, k1_prf=k1_prf, b_prf=b_prf,
                           new_term_weight=weight, num_new_temrs=num_terms, num_docs=num_docs)
    runner = Runner(INDEX, TOPICS, OUTPUT,
                    model_params=params, eval_method="map", qrel_path=QRELS_DEV)
    return runner

def tune_bm25_params():
    runners = []
    for k1 in K1_RANGE:
        for b in B_RANGE:
            runners.append(bm25_runner(k1, b))
    return parallel_tune(runners)


def tune_bm25prf_params(k1, b):
    runners = []
    for k1_prf in PRF_K1_RANGE:
        for b_prf in PRF_B_RANGE:
            for weight in TERM_WEIGHT_RANGE:
                for num_docs in N_DOCS_RANGE:
                    for num_terms in N_TERMS_RANGE:
                        runners.append(bm25prf_runner(k1, b, k1_prf, b_prf,
                                                      num_terms, num_docs, weight))
    return parallel_tune(runners)


def parallel_tune(runners: Runner) -> Params:
    print("%d to run" % len(runners))
    pool = multiprocessing.Pool()
    scores = pool.map(get_eval_result, runners)
    pool.terminate()
    best_runner = None
    highest_score = -999
    for score, runner in zip(scores, runners):
        if score > highest_score:
            highest_score = score
            best_runner = runner
    print("Best Score: %.3f" % highest_score)
    print("Best Params: %s" % best_runner.model_params)
    return best_runner.model_params


def main():
    bm25_params = tune_bm25_params()
    bm25prf_params = tune_bm25prf_params(bm25_params["k1"], bm25_params["b"])
    with open("tuned_params.json", "w") as f:
        json.dump(bm25prf_params, f)
    