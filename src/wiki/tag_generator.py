"""
TF-IDF based tag generation for documents.
"""
from typing import List, Dict
from collections import Counter
import re
import math


class TagGenerator:
    """
    Generate tags for documents using TF-IDF algorithm.
    """
    
    # Common stop words to exclude
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
        'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
        'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
        'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now', 'also'
    }
    
    @staticmethod
    def extract_terms(text: str) -> List[str]:
        """
        Extract terms from text.
        
        Args:
            text: Document text
        
        Returns:
            List of terms
        """
        # Convert to lowercase
        text = text.lower()
        
        # Extract words (alphanumeric + hyphens)
        words = re.findall(r'\b[a-z0-9]+(?:-[a-z0-9]+)*\b', text)
        
        # Filter stop words and short words
        terms = [
            word for word in words
            if word not in TagGenerator.STOP_WORDS and len(word) > 2
        ]
        
        return terms
    
    @staticmethod
    def calculate_tf(terms: List[str]) -> Dict[str, float]:
        """
        Calculate term frequency.
        
        Args:
            terms: List of terms
        
        Returns:
            Dict of term -> TF score
        """
        if not terms:
            return {}
        
        term_counts = Counter(terms)
        total_terms = len(terms)
        
        return {
            term: count / total_terms
            for term, count in term_counts.items()
        }
    
    @staticmethod
    def calculate_idf(all_documents_terms: List[List[str]]) -> Dict[str, float]:
        """
        Calculate inverse document frequency.
        
        Args:
            all_documents_terms: List of term lists for all documents
        
        Returns:
            Dict of term -> IDF score
        """
        if not all_documents_terms:
            return {}
        
        num_documents = len(all_documents_terms)
        
        # Count documents containing each term
        document_frequency = Counter()
        for doc_terms in all_documents_terms:
            unique_terms = set(doc_terms)
            for term in unique_terms:
                document_frequency[term] += 1
        
        # Calculate IDF
        idf = {}
        for term, df in document_frequency.items():
            idf[term] = math.log(num_documents / df)
        
        return idf
    
    @staticmethod
    def generate_tags(
        document_text: str,
        all_documents_texts: List[str],
        max_tags: int = 10,
        min_score: float = 0.01
    ) -> List[Dict[str, float]]:
        """
        Generate tags for a document using TF-IDF.
        
        Args:
            document_text: Text of the document to tag
            all_documents_texts: Texts of all documents in corpus
            max_tags: Maximum number of tags to generate
            min_score: Minimum TF-IDF score threshold
        
        Returns:
            List of dicts with 'tag' and 'score' keys, sorted by score descending
        """
        # Extract terms from all documents
        all_documents_terms = [
            TagGenerator.extract_terms(text)
            for text in all_documents_texts
        ]
        
        # Extract terms from target document
        document_terms = TagGenerator.extract_terms(document_text)
        
        if not document_terms:
            return []
        
        # Calculate TF for target document
        tf = TagGenerator.calculate_tf(document_terms)
        
        # Calculate IDF for corpus
        idf = TagGenerator.calculate_idf(all_documents_terms)
        
        # Calculate TF-IDF scores
        tfidf_scores = {}
        for term in tf:
            if term in idf:
                tfidf_scores[term] = tf[term] * idf[term]
        
        # Filter by minimum score and sort
        tags = [
            {'tag': term, 'score': score}
            for term, score in tfidf_scores.items()
            if score >= min_score
        ]
        
        tags.sort(key=lambda x: x['score'], reverse=True)
        
        return tags[:max_tags]
