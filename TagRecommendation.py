import numpy as np
import csv
import random
import collections
import tensorflow as tf
import matplotlib.pyplot as plt
np.set_printoptions(threshold=np.nan)
%matplotlib inline
from __future__ import print_function
import math
import os
import tensorflow as tf
import zipfile
from matplotlib import pylab
from six.moves import range
from six.moves.urllib.request import urlretrieve
from sklearn.manifold import TSNE
    
############ Preprocessing Tag Data ############
data_num = 30000
sentences = []
data = np.zeros((data_num, 512))
tags = {}
f = open("mirflickr_GIST.txt")
i = 0
for row in csv.reader(f):
    row_num = row[0:512]
    row_num = [float(x) for x in row_num]
        
    if len(row[513:]) < 5:
        continue
    data[i,] = row_num
    tags[i] = row[513:]
    i += 1
    if i == data_num:
        break

new_tags = {}
for key in tags:
    lst = []
    for word in tags[key]:
        lst.append(word[1:])
    new_tags[key] = lst
        
print(new_tags)

def co_occurance_matrix(unique_words):
    co_occurance = {}
    for i in unique_words:
        for j in unique_words:
            if i is not j:
                co_occurance[i + ","+ j] = 0
    for key in co_occurance:
        word1 = key.split(",")[0]
        word2 = key.split(",")[1]
        for word in new_tags.values():
            if word1 in word and word2 in word:
                co_occurance[word1 + "," + word2] = co_occurance[word1 + "," + word2] + 1
    return(co_occurance)

def get_top_list_words(unique_words, co_occurance):
    top_list = {}
    for i in unique_words: top_list[i] = []
    for key in co_occurance:
        word1 = key.split(",")[0]
        word2 = key.split(",")[1]
        for word in top_list:
            if word == word1:
                top_list[word].append((word2, co_occurance[key]))
    
    return(top_list)

def get_individual_count():
    total = []
    for key in new_tags:
        total += new_tags[key]
    count = dict((i, total.count(i)) for i in total)
    return(count)

def get_union_count(unique_words):
    indiv_c = get_individual_count()
    co_matrix = {}
    for i in unique_words:
        for j in unique_words:
            if i is not j:
                co_matrix[i + ","+ j] = indiv_c[i] + indiv_c[j]
    return(co_matrix)

def get_candidate_tags(user_defined_tag, m):
    candi_tag = {}
    for tag in user_defined_tag:
        top_tag = sorted(top_word_list[tag], key = lambda x: x[1], reverse=True)[0:m]
        candi_tag[tag] = top_tag
    return(candi_tag)

def symmetric_measures(occur_mat, unique_words):
    union_count = get_union_count(unique_words)
    for key in occur_mat:
        coeff = []
        for pair in occur_mat[key]:
            word1 = key
            word2 = pair[0]
            union_freq = union_count[word1 + "," + word2]
            coeff.append((pair[0], float(pair[1]) / union_freq))
        occur_mat[key] = coeff
    return(occur_mat)

def asymmetric_measures(occur_mat):
    indiv_count = get_individual_count()
    for key in occur_mat:
        coeff = []
        for pair in occur_mat[key]:
            coeff.append((pair[0], float(pair[1]) / indiv_count[pair[0]]))
        occur_mat[key] = coeff
    return(occur_mat)

def jaccard_coefficient(occur_list, unique_words, version = 1):
    coeff_score = 0
    if version == 1:
        coeff_score = symmetric_measures(occur_list, unique_words)
    else:
        coeff_score = asymmetric_measures(occur_list)
    return(coeff_score)

def vote(user_defined_tag, top_N):
    candi_tag = get_candidate_tags(user_defined_tag, top_N)
    vote_result = {}
    for key in top_word_list:
        vote_result[key] = 0

    for tag in candi_tag:
        candi_lst = [x[0] for x in candi_tag[tag]]
        for word in vote_result:
            if word in candi_lst:
                vote_result[word] = vote_result[tag] + 1
    return(vote_result)

def summing(user_defined_tag, top_N, jac_coeff):
    candi_tag = get_candidate_tags(user_defined_tag, top_N)
    vote_result = {}
    for key in top_word_list:
        vote_result[key] = 0

    for tag in candi_tag:
        candi_lst = [x[0] for x in candi_tag[tag]]
        for word in vote_result:
            related_lst = jac_coeff[tag]
            score = [pair[1] for pair in related_lst if pair[0] == word]
            if len(score) >= 1:
                vote_result[word] = vote_result[word] + score[0]
    return(vote_result)

def stability_promotion(user_defined_tag, Ks = 1):
    indiv_count = get_individual_count()
    stability_mat = {}
    for i in unique_words: stability_mat[i] = 0
    for i in user_defined_tag:
        abs_log_u = abs(Ks - np.log(indiv_count[i]))
        stability = Ks / (Ks + abs_log_u)
        stability_mat[i] = stability
    for i in stability_mat:
        if stability_mat[i] == 0:
            stability_mat[i] = 1
    return(stability_mat)

def descriptiveness_promotion(candidate_tag, Kd = 1):
    indiv_count = get_individual_count()
    descriptiveness_mat = {}
    for i in unique_words: descriptiveness_mat[i] = 0
    for i in candidate_tag:
        abs_log_c = abs(Kd - np.log(indiv_count[i]))
        descrip = Kd / (Kd + abs_log_c)
        descriptiveness_mat[i] = descrip
    return(descriptiveness_mat)

def rank_promotion(user_defined_tag, candidate_tag, unique_words, Kr = 1):
    rank_mat = {}
    rank_list = []
    for i in unique_words:
        for j in unique_words:
            if i is not j:
                rank_mat[i + ","+ j] = 0

    for k in user_defined_tag:
        lst = []
        for pair in candidate_tag[k]:
            lst.append(pair[0])
        rank_list = rank_list + [(i[1], i[0]) for i in enumerate(lst)]
        for pair in rank_list:
            if (Kr + pair[1] - 1) != 0:
                score = float(Kr) / (Kr + pair[1] - 1)
            else:
                score = float(Kr) / (Kr + pair[1])
            rank_mat[k + "," + pair[0]] = score
    return(rank_mat)

def promotion_score(stability, descriptiveness, rank, user_defined_tag, candidate_tag):
    score = {}
    for iteration in candidate_tag:
        i = candidate_tag[iter]
        for j in candidate_tag[iteration]:
            word = j[0]
            result = 100 * stability[iteration] * descriptiveness[word] * rank[iteration + "," + word]
            score[iteration + "," + word] = result
    return(score)

def sum_with_promotion(candidate_tag, user_defined_tag, jac_coeff, promotion_scores):
    sum_result = {}
    for key in top_list:
        sum_result[key] = 0
    for tag in candidate_tag:
        candi_lst = [x[0] for x in candidate_tag[tag]]
        for word in candi_lst:
            related_lst = jac_coeff[tag]
            score = [pair[1] for pair in related_lst if pair[0] == word and pair[0] in candi_lst]
            if len(score) >= 1 and word in candi_lst:
                promotion_key = tag + "," + word
                sum_result[word] = sum_result[word] + (score[0] * promotion_scores[promotion_key])
    return(sum_result)

def vote_with_promotion(candidate_tag, promotion_scores):
    vote_result = {}
    for key in top_word_list:
        vote_result[key] = 0
    for tag in candidate_tag:
        candi_lst = [x[0] for x in candidate_tag[tag]]
        for word in vote_result:
            if word in candi_lst:
                vote_result[word] = vote_result[tag] + (1 * promotion_scores[tag + "," + word])
    print(vote_result)


 ##############
# Experiment #
##############
# Preprocess dataset
new_tags = {}
for key in tags:
    lst = []
    for word in tags[key]:
        lst.append(word[1:])
    new_tags[key] = lst

# set test parameter
user_defined_tag = ['sea', 'sky', 'lake']
top_N = 5
Ks = 1
Kd = 1
Kr = 1

# Calculate Tag Co-occurence Matrix
unique_words = []
for word in new_tags.values():
    for i in word:
        unique_words.append(i)

unique_words = set(unique_words)
co_occurance = co_occurance_matrix(unique_words)
top_list = get_top_list_words(unique_words, co_occurance)
candidate_tags = get_candidate_tags(user_defined_tag, top_N)

#===================== Without Promotion =====================#
################# Voting Strategy #################
top_N = 5
user_define_tags = ['lake', 'sea', 'sky']
result = vote(user_define_tags, 5)
vote_result1 = sorted(result.items(), key=lambda x: x[1], reverse=True)
print(vote_result1)

################# Summing Strategy ################
co_matrix = {}
for i in unique_words:
    for j in unique_words:
        if i is not j:
            co_matrix[i + ","+ j] = 0
jac_coeff = jaccard_coefficient(top_list, unique_words, version = 1)
result = summing(user_defined_tag, top_N, jac_coeff)
summing_result1 = sorted(result.items(), key=lambda x: x[1], reverse=True)
print(summing_result1)

#===================== With Promotion =====================#

################ use Ks = 1 with summing aggregation strategy ################ 
# Stability promotion
stability = stability_promotion(user_defined_tag, Ks = 1)
# Descriptiveness promotion
descriptiveness = descriptiveness_promotion(candidate_tag, Kd = 1)
# Rank promotion
rank = rank_promotion(user_defined_tag, candidate_tag, unique_words, Kr = 1)
# Calculate promotion score
scores = promotion_score(stability, descriptiveness, rank, user_defined_tag, candidate_tag)

result1 = vote_with_promotion(candidate_tag, scores)
print(result1)

################# use Ks = 9 with vote strategy ################ 
# Stability promotion
stability = stability_promotion(user_defined_tag, Ks = 9)
# Descriptiveness promotion
descriptiveness = descriptiveness_promotion(candidate_tag, Kd = 1)
# Rank promotion
rank = rank_promotion(user_defined_tag, candidate_tag, unique_words, Kr = 1)
# Calculate promotion score
scores = promotion_score(stability, descriptiveness, rank, user_defined_tag, candidate_tag)

result2 = sum_with_promotion(candidate_tag, user_defined_tag, jac_coeff, scores)
print(result2)

################# use Kd = 12 with summing aggregation strategy ################ 
# Stability promotion
stability = stability_promotion(user_defined_tag, Ks = 0)
# Descriptiveness promotion
descriptiveness = descriptiveness_promotion(candidate_tag, Kd = 12)
# Rank promotion
rank = rank_promotion(user_defined_tag, candidate_tag, unique_words, Kr = 1)
# Calculate promotion score
scores = promotion_score(stability, descriptiveness, rank, user_defined_tag, candidate_tag)

result3 = sum_with_promotion(candidate_tag, user_defined_tag, jac_coeff, scores)
print(result3)

################# use Kd = 11 with vote strategy ################ 
# Stability promotion
stability = stability_promotion(user_defined_tag, Ks = 0)
# Descriptiveness promotion
descriptiveness = descriptiveness_promotion(candidate_tag, Kd = 11)
# Rank promotion
rank = rank_promotion(user_defined_tag, candidate_tag, unique_words, Kr = 1)
# Calculate promotion score
scores = promotion_score(stability, descriptiveness, rank, user_defined_tag, candidate_tag)

result4 = sum_with_promotion(candidate_tag, user_defined_tag, jac_coeff, scores)
print(result4)