import json
import traceback
from typing import List, Optional, Tuple, Type, cast

import dash_bootstrap_components as dbc
from dash import ALL, Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel, StructuredText
from envinorma.parametrization import AlternativeSection, AMWarning, Condition, InapplicableSection, ParameterElement
from envinorma.parametrization.exceptions import ParametrizationError

from back_office.components.condition_form import callbacks as condition_form_callbacks
from back_office.components.condition_form import condition_form
from back_office.helpers.texts import get_truncated_str
from back_office.routing import Routing
from back_office.utils import DATA_FETCHER, AMOperation

from . import page_ids as ids
from .form_handling import FormHandlingError, extract_and_upsert_new_parameter
from .target_sections_form import DropdownOptions, TargetSectionFormValues
from .target_sections_form import add_callbacks as target_section_form_callbacks
from .target_sections_form import target_section_form


def _title(operation: AMOperation, is_edition: bool, destination_id: Optional[str]) -> str:
    if operation == AMOperation.ADD_CONDITION:
        return (
            f'Condition de non-application #{destination_id}' if is_edition else 'Nouvelle condition de non-application'
        )
    if operation == AMOperation.ADD_ALTERNATIVE_SECTION:
        return f'Paragraphe alternatif #{destination_id}' if is_edition else 'Nouveau paragraphe alternatif'
    if operation == AMOperation.ADD_WARNING:
        return f'Avertissement #{destination_id}' if is_edition else 'Nouvel avertissement'
    raise NotImplementedError(f'Unhandled operation {operation}')


def _main_title(operation: AMOperation, is_edition: bool, destination_id: Optional[str]) -> Component:
    return html.H4(_title(operation, is_edition, destination_id))


def _go_back_button(am_id: str) -> Component:
    return dcc.Link('< Retour', className='btn btn-link', href=Routing.parametrization_path(am_id))


def _save_button(am_id: str) -> Component:
    btn = html.Button('Enregistrer', id='submit-val-param-edition', className='btn btn-primary', n_clicks=0)
    return html.Div([btn], style={'margin-top': '10px', 'margin-bottom': '100px'})


def _get_delete_button(is_edition: bool) -> Component:
    return html.Button(
        'Supprimer',
        id='param-edition-delete-button',
        className='btn btn-danger',
        style={'margin-right': '5px'},
        n_clicks=0,
        hidden=not is_edition,
    )


def _add_block_button(is_edition: bool) -> Component:
    txt = 'Ajouter un paragraphe'
    btn = html.Button(txt, className='mt-2 mb-2 btn btn-light btn-sm', id=ids.ADD_TARGET_BLOCK)
    return html.Div(btn, hidden=is_edition)


def _get_target_section_block(
    operation: AMOperation,
    text_title_options: DropdownOptions,
    loaded_parameter: Optional[ParameterElement],
    am: ArreteMinisteriel,
    is_edition: bool,
) -> Component:
    blocks = [target_section_form(operation, text_title_options, loaded_parameter, am, 0, is_edition)]
    return html.Div(
        [html.H5('Paragraphes visés'), html.Div(blocks, id=ids.TARGET_BLOCKS), _add_block_button(is_edition)]
    )


def _extract_condition(loaded_parameter: ParameterElement) -> Condition:
    if isinstance(loaded_parameter, AMWarning):
        raise ValueError(
            f'loaded_parameter should be of type ParameterElementWithCondition, not {type(loaded_parameter)}'
        )
    return loaded_parameter.condition


def _condition_form(operation: AMOperation, loaded_parameter: Optional[ParameterElement]) -> Component:
    condition = (
        _extract_condition(loaded_parameter) if loaded_parameter and operation != AMOperation.ADD_WARNING else None
    )
    return html.Div(
        [condition_form(condition, ids.CONDITION)],
        hidden=operation == AMOperation.ADD_WARNING,
    )


def _extract_warning_default_value(loaded_parameter: Optional[ParameterElement]) -> str:
    if not loaded_parameter:
        return ''
    if isinstance(loaded_parameter, AMWarning):
        return loaded_parameter.text
    return ''


def _warning_content_text_area(loaded_parameter: Optional[ParameterElement]) -> Component:
    default_value = _extract_warning_default_value(loaded_parameter)
    return dcc.Textarea(
        id=ids.WARNING_CONTENT,
        className='form-control',
        value=default_value,
        style={'min-height': '300px'},
    )


def _warning_content_form(operation: AMOperation, loaded_parameter: Optional[ParameterElement]) -> Component:
    return html.Div(
        [
            html.Label('Contenu de l\'avertissement', className='form-label'),
            _warning_content_text_area(loaded_parameter),
        ],
        hidden=operation != AMOperation.ADD_WARNING,
    )


def _fields(
    text_title_options: DropdownOptions,
    operation: AMOperation,
    loaded_parameter: Optional[ParameterElement],
    destination_id: Optional[str],
    am: ArreteMinisteriel,
) -> Component:
    is_edition = destination_id is not None
    fields = [
        _go_back_button(am.id or ''),
        _main_title(operation, is_edition=is_edition, destination_id=destination_id),
        _get_delete_button(is_edition=is_edition),
        _get_target_section_block(operation, text_title_options, loaded_parameter, am, is_edition=is_edition),
        _warning_content_form(operation, loaded_parameter),
        _condition_form(operation, loaded_parameter),
    ]
    return html.Div(fields)


def _make_form(
    am_id: str,
    text_title_options: DropdownOptions,
    operation: AMOperation,
    loaded_parameter: Optional[ParameterElement],
    destination_id: Optional[str],
    am: ArreteMinisteriel,
) -> Component:
    return html.Div(
        [
            _fields(text_title_options, operation, loaded_parameter, destination_id, am),
            html.Div(id='param-edition-upsert-output', className='mt-2'),
            html.Div(id='param-edition-delete-output'),
            dcc.Store(id=ids.DROPDOWN_OPTIONS, data=json.dumps(text_title_options)),
            _save_button(am_id),
        ]
    )


def _extract_reference_and_values_titles(text: StructuredText, level: int) -> List[Tuple[str, str]]:
    return [(text.id, get_truncated_str('#' * level + ' ' + text.title.text))] + [
        elt for sec in text.sections for elt in _extract_reference_and_values_titles(sec, level + 1)
    ]


def _extract_paragraph_reference_dropdown_values(am: ArreteMinisteriel) -> DropdownOptions:
    title_references_and_values = [elt for sec in am.sections for elt in _extract_reference_and_values_titles(sec, 1)]
    return [{'label': title, 'value': reference} for reference, title in title_references_and_values]


def parameter_element_form(
    am_id: str,
    am: ArreteMinisteriel,
    operation: AMOperation,
    loaded_parameter: Optional[ParameterElement],
    destination_id: Optional[str],
) -> Component:
    dropdown_values = _extract_paragraph_reference_dropdown_values(am)
    return _make_form(am_id, dropdown_values, operation, loaded_parameter, destination_id, am)


def _handle_submit(
    operation: AMOperation,
    am_id: str,
    parameter_id: Optional[str],
    target_section_form_values: TargetSectionFormValues,
    condition: Optional[str],
    warning_content: str,
) -> Component:
    try:
        extract_and_upsert_new_parameter(
            operation,
            am_id,
            parameter_id,
            target_section_form_values,
            condition,
            warning_content,
        )
    except FormHandlingError as exc:
        return dbc.Alert(f'Erreur dans le formulaire:\n{exc}', color='danger')
    except ParametrizationError as exc:
        return dbc.Alert(
            f'Erreur: la section visée est déjà visée par au moins une autre condition.'
            f' Celle-ci est incompatible avec celle(s) déjà définie(s) :\n{exc}',
            color='danger',
        )
    except Exception:  # pylint: disable=broad-except
        return dbc.Alert(f'Unexpected error:\n{traceback.format_exc()}', color='danger')
    return html.Div(
        [
            dbc.Alert('Enregistrement réussi.', color='success'),
            dcc.Location(pathname=Routing.parametrization_path(am_id), id='param-edition-success-redirect'),
        ]
    )


def _deduce_parameter_object_type(operation: AMOperation) -> Type[ParameterElement]:
    if operation == AMOperation.ADD_ALTERNATIVE_SECTION:
        return AlternativeSection
    if operation == AMOperation.ADD_CONDITION:
        return InapplicableSection
    if operation == AMOperation.ADD_WARNING:
        return AMWarning
    raise NotImplementedError()


def _handle_delete(n_clicks: int, operation_str: str, am_id: str, parameter_id: str) -> Component:
    if n_clicks == 0:
        return html.Div()
    try:
        operation = AMOperation(operation_str)
        DATA_FETCHER.remove_parameter(am_id, _deduce_parameter_object_type(operation), parameter_id)
    except Exception:  # pylint: disable=broad-except
        return dbc.Alert(f'Unexpected error:\n{traceback.format_exc()}', color='danger')
    return html.Div(
        [
            dbc.Alert('Suppression réussie.', color='success'),
            dcc.Location(pathname=Routing.parametrization_path(am_id), id='param-edition-success-redirect'),
        ]
    )


def add_callbacks(app: Dash):
    condition_form_callbacks(ids.CONDITION)(app)
    target_section_form_callbacks(app)

    @app.callback(
        Output('param-edition-upsert-output', 'children'),
        Input('submit-val-param-edition', 'n_clicks'),
        State(ids.AM_OPERATION, 'data'),
        State(ids.AM_ID, 'data'),
        State(ids.PARAMETER_ID, 'data'),
        State(ids.WARNING_CONTENT, 'value'),
        State(ids.new_text_title(cast(int, ALL)), 'value'),
        State(ids.new_text_content(cast(int, ALL)), 'value'),
        State(ids.target_section(cast(int, ALL)), 'value'),
        State(ids.target_alineas(cast(int, ALL)), 'value'),
        State(ids.propagate_in_subsection(cast(int, ALL)), 'value'),
        State(ids.CONDITION, 'data'),
        prevent_initial_call=True,
    )
    def handle_submit(
        _,
        operation_str,
        am_id,
        parameter_id,
        warning_content,
        new_texts_titles,
        new_texts_contents,
        target_sections,
        target_alineas,
        propagate_in_subsection,
        condition,
    ):
        target_section_form_values = TargetSectionFormValues(
            new_texts_titles, new_texts_contents, target_sections, target_alineas, propagate_in_subsection
        )
        return _handle_submit(
            AMOperation(operation_str), am_id, parameter_id, target_section_form_values, condition, warning_content
        )

    @app.callback(
        Output('param-edition-delete-output', 'children'),
        Input('param-edition-delete-button', 'n_clicks'),
        State(ids.AM_OPERATION, 'data'),
        State(ids.AM_ID, 'data'),
        State(ids.PARAMETER_ID, 'data'),
    )
    def handle_delete(n_clicks, operation, am_id, parameter_id):
        return _handle_delete(n_clicks, operation, am_id, parameter_id)

    @app.callback(
        Output(ids.TARGET_BLOCKS, 'children'),
        Input(ids.ADD_TARGET_BLOCK, 'n_clicks'),
        State(ids.TARGET_BLOCKS, 'children'),
        State(ids.AM_OPERATION, 'data'),
        State(ids.DROPDOWN_OPTIONS, 'data'),
        prevent_initial_call=True,
    )
    def add_block(n_clicks, children, operation_str, options_str):
        new_block = target_section_form(
            AMOperation(operation_str), json.loads(options_str), None, None, n_clicks + 1, False
        )
        return children + [new_block]
