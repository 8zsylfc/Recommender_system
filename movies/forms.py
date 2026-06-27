from __future__ import annotations

from django import forms


class CrawlForm(forms.Form):
    url = forms.URLField(label="电影列表页 URL", help_text="建议使用“列表页/搜索结果页”")
    limit = forms.IntegerField(label="最多抓取条数", min_value=1, max_value=500, initial=50)


class RatingForm(forms.Form):
    score = forms.ChoiceField(
        label="评分",
        choices=[(i, f"{i} 星") for i in range(1, 6)],
        widget=forms.RadioSelect,
    )

