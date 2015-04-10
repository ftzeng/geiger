import lda
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from nltk import sent_tokenize
from geiger.text import strip_tags, Tokenizer
from geiger.util.progress import Progress
import logging


# Silence handlers from the `lda` library,
# this is probably overkill :\
logger = logging.getLogger('lda')
logger.handlers = []

class Model():
    """
    LDA (Latent Dirichlet Allocation) model
    for unsupervised topic modeling.

    TO DO:
        - this model has to be rebuilt for each comment section as new comments come in - what's the best way to manage that?

    Notes:
        - tried LDA on individual sentences, doesn't work as well.
    """

    def __init__(self, n_topics=None, verbose=False):
        """
        Args:
            | topics            -- int or None, number of topics. If None, will try a range to maximize the log likelihood.
        """
        self.verbose = verbose
        self.n_topics = n_topics
        self.vectr = CountVectorizer(stop_words='english', ngram_range=(1,1), tokenizer=Tokenizer())

    def train(self, comments):
        """
        Build the topic model from a list of documents (strings).

        Assumes documents have been pre-processed (e.g. stripped of HTML, etc)
        """
        docs = [c.body for c in comments]
        vecs = self.vectr.fit_transform(docs)

        # If n_topics is not specified, try a range.
        if self.n_topics is None:
            # Try n_topics in [5, 20] in steps of 2.
            n_topics_range = np.arange(5, 20, 2)

            results = []
            models = []
            p = Progress('LDA')
            n = len(n_topics_range) - 1
            for i, n in enumerate(n_topics_range):
                p.print_progress(i/n)
                model = lda.LDA(n_topics=n, n_iter=2000, random_state=1)
                model.fit_transform(vecs)
                models.append(model)
                results.append(model.loglikelihood())

                if self.verbose:
                    self.print_topics(model)

            i = np.argmax(results)
            self.n_topics = n_topics_range[i]
            self.m = models[i]
            print('Selected n_topics={0}'.format(self.n_topics))

        else:
            self.m = lda.LDA(n_topics=self.n_topics, n_iter=2000, random_state=1)
            self.m.fit_transform(vecs)
            if self.verbose:
                self.print_topics(self.m)

    def identify(self, docs):
        """
        Labels a list of documents with
        their topic and probability for that topic.
        """
        vecs = self.vectr.transform(docs)

        # Seems to a bug where the `transform` method can't accept sparse matrices?
        doc_topic = self.m.transform(vecs.toarray())
        for i, doc in enumerate(docs):
            topic = doc_topic[i].argmax()
            proba = doc_topic[i][topic]
            yield doc, topic, proba

    @property
    def topic_dists(self):
        return self.m.doc_topic_

    def cluster(self, comments):
        """
        Build clusters out of most likely topics.
        """

        # If no model exists, train it.
        if not hasattr(self, 'm'):
            self.train(comments)

        clusters = [[] for _ in range(self.n_topics)]
        for i, comment in enumerate(comments):
            topic = self.m.doc_topic_[i].argmax()
            clusters[topic].append(comment)

        return clusters

    def print_topics(self, model):
        """
        Prints out the top words for each topic in the model.
        """
        n_top_words = 8
        topic_word = model.components_
        vocab = self.vectr.get_feature_names()
        for i, topic_dist in enumerate(topic_word):
            topic_words = np.array(vocab)[np.argsort(topic_dist)][:-n_top_words:-1]
            print('Topic: {}: {}'.format(i, ' | '.join(topic_words)))
        print('---')
