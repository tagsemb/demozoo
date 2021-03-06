from django import forms
from unidecode import unidecode

from demoscene.index import name_indexer, complete_indexer, name_indexer_with_real_names, complete_indexer_with_real_names

class SearchForm(forms.Form):
	q = forms.CharField(required=True, label='Search')
	
	def search(self, with_real_names=False):
		query = unidecode(self.cleaned_data['q'])
		name_results = (name_indexer_with_real_names if with_real_names else name_indexer).search(query).prefetch()
		name_result_ids = set([hit.pk for hit in name_results])
		complete_results = (complete_indexer_with_real_names if with_real_names else complete_indexer).search(query).prefetch()
		# need to filter name_result_ids out from other_results manually,
		# because CompositeIndexer doesn't support filtering:
		# http://code.google.com/p/djapian/issues/detail?id=66
		other_results = []
		for r in complete_results:
			if r.pk not in name_result_ids:
				other_results.append(r)
		return (name_results, other_results, complete_results)
