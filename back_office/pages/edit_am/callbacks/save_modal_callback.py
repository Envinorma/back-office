import traceback
from typing import Dict, List, Optional

from dash import Dash, Input, Output, State, html
from dash.development.base_component import Component
from envinorma.models.lost_topic import LostTopic

from back_office.components import error_component, primary_alert_component, success_component
from back_office.utils import DATA_FETCHER

from .. import ids
from .save_callback import TextAreaHandlingError, extract_text_from_html


def _list_lost_parameters_titles(orphan_titles: Dict[str, List[str]], am_id: str) -> List[List[str]]:
    parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
    lost_parameters: List[List[str]] = []
    for element in parametrization.elements():
        if element.section_id in orphan_titles:
            lost_parameters.append(orphan_titles[element.section_id])
    return lost_parameters


def _stringify_lost_topic(lost_topic: LostTopic) -> str:
    return '- Thème {}\n- Titres : {}\n'.format(lost_topic.topic.value, ' / '.join(lost_topic.section_titles))


def _stringify_lost_topics(lost_topics: List[LostTopic]) -> str:
    return '\n'.join(map(_stringify_lost_topic, lost_topics))


def _lost_topics_message(lost_topics: List[LostTopic]) -> str:
    lost_topics_str = _stringify_lost_topics(lost_topics)
    if len(lost_topics) > 1:
        return (
            f'Les {len(lost_topics)} thèmes suivants n\'ont pas pu être réaffectés :\n{lost_topics_str}\n'
            'Pensez à mettre à jour les thèmes si vous validez l\'enregistrement.'
        )
    return f'Le thème suivant n\'a pas pu être réaffecté :\n{lost_topics_str}. Pensez à le réaffecter si nécessaire.'


def _topic_component(lost_topics: List[LostTopic]) -> Component:
    if not lost_topics:
        return success_component("Aucun thème associé aux sections ne sera perdu par la mise à jour de l'AM.")
    return primary_alert_component(_lost_topics_message(lost_topics))


def _stringify_lost_parameter(lost_parameter_titles: List[str]) -> str:
    return ' / '.join(lost_parameter_titles)


def _stringify_lost_parameters(lost_parameters: List[List[str]]) -> str:
    return '\n'.join(map(_stringify_lost_parameter, lost_parameters))


def _lost_parameters_message(lost_parameters: List[List[str]]) -> str:
    lost_parameters_str = _stringify_lost_parameters(lost_parameters)
    if len(lost_parameters) > 1:
        return (
            f'{len(lost_parameters)} paramètres n\'ont pas pu être réaffectés :\n{lost_parameters_str}\n\n '
            'Pensez à mettre à jour le paramétrage si vous validez l\'enregistrement.'
        )
    return (
        f'Le paramètre suivant n\'a pas pu être réaffecté :\n{lost_parameters_str}.\n\n '
        'Pensez à mettre à jour le paramétrage si vous validez l\'enregistrement.'
    )


def _parameter_component(lost_parameter_titles: List[List[str]]) -> Component:
    if not lost_parameter_titles:
        return success_component("Aucun paramètre associé aux sections ne sera perdu par la mise à jour de l'AM.")
    return primary_alert_component(_lost_parameters_message(lost_parameter_titles))


def _lost_topics_and_parameters(am_id: str, form_am_value: Optional[str]) -> Component:
    if not form_am_value:
        raise TextAreaHandlingError('Le formulaire est vide.')
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        return success_component("Extraction de l'arrêté ministériel réussie. Confirmer l'enregistrement ?")
    new_am, lost_topics = am.create_copy_with_new_content(extract_text_from_html(form_am_value))
    lost_parameters_titles = _list_lost_parameters_titles(new_am.orphan_titles or {}, am_id)
    return html.Div(
        [
            _topic_component(lost_topics),
            _parameter_component(lost_parameters_titles),
        ]
    )


def _lost_topics_and_parameters_catch(am_id: str, form_am_value: Optional[str]) -> Component:
    try:
        return _lost_topics_and_parameters(am_id, form_am_value)
    except TextAreaHandlingError as exc:
        return error_component(str(exc))
    except Exception:
        message = f'Impossible de vérifier le contenu. Erreur :\n{traceback.format_exc()}'
        return error_component(message)


def add_callbacks(app: Dash) -> None:
    @app.callback(
        Output(ids.SAVE_MODAL, 'is_open'),
        Input(ids.PRESAVE_BUTTON, 'n_clicks'),
        Input(ids.SAVE_BUTTON, 'n_clicks'),
        State(ids.SAVE_MODAL, 'is_open'),
        prevent_initial_call=True,
    )
    def _toggle_modal(n_clicks, n_clicks_submit, is_open):
        if n_clicks or n_clicks_submit:
            return not is_open
        return False

    @app.callback(
        Output(ids.SAVE_MODAL_BODY, 'children'),
        Input(ids.PRESAVE_BUTTON, 'n_clicks'),
        State(ids.AM_ID, 'data'),
        State(ids.TEXT_AREA_COMPONENT, 'value'),
        prevent_initial_call=True,
    )
    def _build_lost_topics_and_parameters(_, am_id, form_am_value):
        return _lost_topics_and_parameters_catch(am_id, form_am_value)
