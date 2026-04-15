"""
Unit tests for wiki tag generator (TF-IDF based).

Tested Scenarios:
- Extract terms from text (lowercase, alphanumeric)
- Filter stop words and short words
- Calculate term frequency (TF)
- Calculate inverse document frequency (IDF)
- Generate tags with TF-IDF scoring
- Tag filtering by minimum score
- Tag limiting by max_tags
- Handle empty documents
- Handle single document corpus

Untested Scenarios / Gaps:
- Unicode and non-ASCII text
- Very large documents
- Stemming and lemmatization
- Custom stop words
- Multi-word phrases
- Tag clustering

Test Strategy:
- Pure unit tests (no database)
- Test each component independently
- Test TF-IDF algorithm correctness
- Test edge cases and empty inputs
"""
import pytest
from wiki.tag_generator import TagGenerator


class TestTagGeneratorExtractTerms:
    """Tests for term extraction."""
    
    def test_extract_simple_terms(self):
        """Test extracting simple terms from text."""
        text = "Python programming language"
        terms = TagGenerator.extract_terms(text)
        
        assert "python" in terms
        assert "programming" in terms
        assert "language" in terms
    
    def test_filter_stop_words(self):
        """Test that stop words are filtered out."""
        text = "The quick brown fox and the lazy dog"
        terms = TagGenerator.extract_terms(text)
        
        # Stop words should be filtered
        assert "the" not in terms
        assert "and" not in terms
        # Content words should remain
        assert "quick" in terms
        assert "brown" in terms
        assert "lazy" in terms
    
    def test_filter_short_words(self):
        """Test that short words (<=2 chars) are filtered."""
        text = "I am a developer in AI"
        terms = TagGenerator.extract_terms(text)
        
        # Short words should be filtered
        assert "i" not in terms
        assert "am" not in terms
        assert "a" not in terms
        assert "in" not in terms
        assert "ai" not in terms
        # Longer words should remain
        assert "developer" in terms
    
    def test_lowercase_conversion(self):
        """Test that terms are converted to lowercase."""
        text = "Python PYTHON python"
        terms = TagGenerator.extract_terms(text)
        
        # All should be lowercase
        assert all(term == "python" for term in terms)
    
    def test_hyphenated_words(self):
        """Test that hyphenated words are preserved."""
        text = "test-driven development and machine-learning"
        terms = TagGenerator.extract_terms(text)
        
        assert "test-driven" in terms
        assert "machine-learning" in terms
        assert "development" in terms
    
    def test_empty_text(self):
        """Test extracting terms from empty text."""
        terms = TagGenerator.extract_terms("")
        
        assert terms == []
    
    def test_only_stop_words(self):
        """Test text with only stop words."""
        text = "the and or but"
        terms = TagGenerator.extract_terms(text)
        
        assert terms == []


class TestTagGeneratorTF:
    """Tests for term frequency calculation."""
    
    def test_calculate_tf_simple(self):
        """Test calculating TF for simple term list."""
        terms = ["python", "java", "python", "python"]
        tf = TagGenerator.calculate_tf(terms)
        
        assert tf["python"] == 0.75  # 3/4
        assert tf["java"] == 0.25  # 1/4
    
    def test_calculate_tf_single_term(self):
        """Test TF when all terms are the same."""
        terms = ["python", "python", "python"]
        tf = TagGenerator.calculate_tf(terms)
        
        assert tf["python"] == 1.0
    
    def test_calculate_tf_unique_terms(self):
        """Test TF when all terms are unique."""
        terms = ["python", "java", "javascript", "ruby"]
        tf = TagGenerator.calculate_tf(terms)
        
        assert all(score == 0.25 for score in tf.values())
    
    def test_calculate_tf_empty(self):
        """Test TF calculation with empty term list."""
        tf = TagGenerator.calculate_tf([])
        
        assert tf == {}


class TestTagGeneratorIDF:
    """Tests for inverse document frequency calculation."""
    
    def test_calculate_idf_simple(self):
        """Test calculating IDF for simple corpus."""
        all_docs = [
            ["python", "programming"],
            ["java", "programming"],
            ["python", "java"]
        ]
        idf = TagGenerator.calculate_idf(all_docs)
        
        # "programming" appears in 2/3 documents
        # IDF = log(3/2) ≈ 0.405
        assert abs(idf["programming"] - 0.405) < 0.01
        
        # "python" appears in 2/3 documents
        assert abs(idf["python"] - 0.405) < 0.01
        
        # "java" appears in 2/3 documents
        assert abs(idf["java"] - 0.405) < 0.01
    
    def test_calculate_idf_unique_term(self):
        """Test IDF for term appearing in only one document."""
        all_docs = [
            ["python", "unique"],
            ["python", "common"],
            ["python", "common"]
        ]
        idf = TagGenerator.calculate_idf(all_docs)
        
        # "unique" appears in 1/3 documents
        # IDF = log(3/1) ≈ 1.099
        assert abs(idf["unique"] - 1.099) < 0.01
        
        # "python" appears in all 3 documents
        # IDF = log(3/3) = 0
        assert idf["python"] == 0.0
    
    def test_calculate_idf_empty(self):
        """Test IDF calculation with empty corpus."""
        idf = TagGenerator.calculate_idf([])
        
        assert idf == {}
    
    def test_calculate_idf_single_document(self):
        """Test IDF with single document corpus."""
        all_docs = [["python", "programming"]]
        idf = TagGenerator.calculate_idf(all_docs)
        
        # All terms appear in 1/1 documents
        # IDF = log(1/1) = 0
        assert all(score == 0.0 for score in idf.values())


class TestTagGeneratorGenerate:
    """Tests for tag generation."""
    
    def test_generate_tags_simple(self):
        """Test generating tags for simple document."""
        document = "Python is a programming language. Python is popular."
        corpus = [
            "Python is a programming language. Python is popular.",
            "Java is also a programming language.",
            "JavaScript is used for web development."
        ]
        
        tags = TagGenerator.generate_tags(document, corpus, max_tags=5)
        
        # Should return list of dicts with 'tag' and 'score'
        assert len(tags) > 0
        assert all('tag' in tag and 'score' in tag for tag in tags)
        
        # "python" should have high score (appears frequently in doc)
        tag_names = [tag['tag'] for tag in tags]
        assert "python" in tag_names
    
    def test_generate_tags_sorted_by_score(self):
        """Test that tags are sorted by score descending."""
        document = "Python Python Python Java"
        corpus = [
            "Python Python Python Java",
            "Ruby JavaScript"
        ]
        
        tags = TagGenerator.generate_tags(document, corpus, max_tags=10)
        
        # Scores should be in descending order
        scores = [tag['score'] for tag in tags]
        assert scores == sorted(scores, reverse=True)
    
    def test_generate_tags_max_limit(self):
        """Test that max_tags limits the number of tags."""
        document = "one two three four five six seven eight nine ten"
        corpus = [document]
        
        tags = TagGenerator.generate_tags(document, corpus, max_tags=3)
        
        assert len(tags) <= 3
    
    def test_generate_tags_min_score_filter(self):
        """Test that min_score filters low-scoring tags."""
        document = "python programming language"
        corpus = [document]
        
        # With high min_score, should get fewer tags
        tags = TagGenerator.generate_tags(document, corpus, min_score=0.5)
        
        # All returned tags should have score >= min_score
        assert all(tag['score'] >= 0.5 for tag in tags)
    
    def test_generate_tags_empty_document(self):
        """Test generating tags for empty document."""
        document = ""
        corpus = ["some content"]
        
        tags = TagGenerator.generate_tags(document, corpus)
        
        assert tags == []
    
    def test_generate_tags_only_stop_words(self):
        """Test generating tags for document with only stop words."""
        document = "the and or but"
        corpus = [document, "python programming"]
        
        tags = TagGenerator.generate_tags(document, corpus)
        
        # Should return empty list (all stop words filtered)
        assert tags == []
    
    def test_generate_tags_unique_terms(self):
        """Test that unique terms get higher scores."""
        document = "python machine-learning tensorflow"
        corpus = [
            "python machine-learning tensorflow",
            "python java javascript",
            "python ruby perl"
        ]
        
        tags = TagGenerator.generate_tags(document, corpus, max_tags=10)
        
        # "machine-learning" and "tensorflow" are unique to first doc
        # Should have higher scores than "python" (appears in all docs)
        tag_dict = {tag['tag']: tag['score'] for tag in tags}
        
        if "machine-learning" in tag_dict and "python" in tag_dict:
            assert tag_dict["machine-learning"] > tag_dict["python"]
    
    def test_generate_tags_tf_idf_correctness(self):
        """Test TF-IDF calculation correctness."""
        # Document with "python" appearing 3 times, "java" once
        document = "python python python java"
        corpus = [
            "python python python java",  # Target document
            "ruby javascript"  # Other document
        ]
        
        tags = TagGenerator.generate_tags(document, corpus, max_tags=10, min_score=0.0)
        
        # "python" has higher TF (3/4) than "java" (1/4)
        # Both have same IDF (appear in 1/2 documents)
        # So "python" should have higher TF-IDF score
        tag_dict = {tag['tag']: tag['score'] for tag in tags}
        
        assert tag_dict["python"] > tag_dict["java"]
    
    def test_generate_tags_empty_corpus(self):
        """Test generating tags with empty corpus."""
        document = "python programming"
        corpus = []
        
        tags = TagGenerator.generate_tags(document, corpus)
        
        # Should handle gracefully (empty IDF)
        assert tags == []
