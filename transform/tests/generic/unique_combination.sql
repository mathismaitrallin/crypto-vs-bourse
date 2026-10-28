{#
    Échoue si une même combinaison de colonnes apparaît plusieurs fois.
    Exemple : une seule ligne par (symbol, date).
#}
{% test unique_combination(model, columns) %}

select
    {{ columns | join(', ') }},
    count(*) as nb_occurrences
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1

{% endtest %}
