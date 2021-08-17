import json
import traceback
from typing import List, Optional, Tuple, Type, cast

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component
from envinorma.models import Ints, StructuredText, dump_path
from envinorma.parametrization import (
    AlternativeSection,
    AMWarning,
    Condition,
    ConditionSource,
    InapplicableSection,
    ParameterObject,
)
from envinorma.parametrization.exceptions import ParametrizationError

from back_office.app_init import app
from back_office.helpers.texts import get_truncated_str
from back_office.routing import build_am_page
from back_office.utils import DATA_FETCHER, AMOperation

from . import page_ids
from .condition_form import ConditionFormValues, condition_form
from .form_handling import FormHandlingError, extract_and_upsert_new_parameter
from .target_sections_form import DropdownOptions, TargetSectionFormValues, target_section_form


def _title(operation: AMOperation, is_edition: bool, rank: int) -> str:
    if operation == AMOperation.ADD_CONDITION:
        return f'Condition de non-application n°{rank}' if is_edition else 'Nouvelle condition de non-application'
    if operation == AMOperation.ADD_ALTERNATIVE_SECTION:
        return f'Paragraphe alternatif n°{rank}' if is_edition else 'Nouveau paragraphe alternatif'
    if operation == AMOperation.ADD_WARNING:
        return f'Avertissement n°{rank}' if is_edition else 'Nouvel avertissement'
    if operation in (AMOperation.EDIT_STRUCTURE, AMOperation.INIT):
        raise ValueError(f'Unexpected operation {operation}')
    raise NotImplementedError(f'Unhandled operation {operation}')


def _main_title(operation: AMOperation, is_edition: bool, rank: int) -> Component:
    return html.H4(_title(operation, is_edition, rank))


def _go_back_button(parent_page: str) -> Component:
    return dcc.Link(html.Button('Retour', className='btn btn-link center'), href=parent_page)


def _buttons(parent_page: str) -> Component:
    return html.Div(
        [
            html.Button(
                'Enregistrer',
                id='submit-val-param-edition',
                className='btn btn-primary',
                style={'margin-right': '5px'},
                n_clicks=0,
            ),
            _go_back_button(parent_page),
        ],
        style={'margin-top': '10px', 'margin-bottom': '100px'},
    )


def _extract_source(loaded_parameter: ParameterObject) -> ConditionSource:
    if isinstance(loaded_parameter, AMWarning):
        raise ValueError(
            f'loaded_parameter should be of type ParameterObjectWithCondition, not {type(loaded_parameter)}'
        )
    return loaded_parameter.source


def _get_source_form(
    operation: AMOperation, options: DropdownOptions, loaded_parameter: Optional[ParameterObject]
) -> Component:
    if operation != AMOperation.ADD_WARNING and loaded_parameter:
        default_value = dump_path(_extract_source(loaded_parameter).reference.section.path)
    else:
        default_value = ''
    dropdown_source = dcc.Dropdown(
        value=default_value, options=options, id=page_ids.SOURCE, style={'font-size': '0.8em'}
    )
    return html.Div([html.H5('Source'), dropdown_source], hidden=operation == AMOperation.ADD_WARNING)


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
    btn = html.Button(txt, className='mt-2 mb-2 btn btn-light btn-sm', id=page_ids.ADD_TARGET_BLOCK)
    return html.Div(btn, hidden=is_edition)


def _get_target_section_block(
    operation: AMOperation,
    text_title_options: DropdownOptions,
    loaded_parameter: Optional[ParameterObject],
    text: StructuredText,
    is_edition: bool,
) -> Component:
    blocks = [target_section_form(operation, text_title_options, loaded_parameter, text, 0, is_edition)]
    return html.Div(
        [html.H5('Paragraphes visés'), html.Div(blocks, id=page_ids.TARGET_BLOCKS), _add_block_button(is_edition)]
    )


def _extract_condition(loaded_parameter: ParameterObject) -> Condition:
    if isinstance(loaded_parameter, AMWarning):
        raise ValueError(
            f'loaded_parameter should be of type ParameterObjectWithCondition, not {type(loaded_parameter)}'
        )
    return loaded_parameter.condition


def _condition_form(operation: AMOperation, loaded_parameter: Optional[ParameterObject]) -> Component:
    condition = (
        _extract_condition(loaded_parameter) if loaded_parameter and operation != AMOperation.ADD_WARNING else None
    )
    return html.Div(
        [condition_form(condition)],
        hidden=operation == AMOperation.ADD_WARNING,
    )


def _extract_warning_default_value(loaded_parameter: Optional[ParameterObject]) -> str:
    if not loaded_parameter:
        return ''
    if isinstance(loaded_parameter, AMWarning):
        return loaded_parameter.text
    return ''


def _warning_content_text_area(loaded_parameter: Optional[ParameterObject]) -> Component:
    default_value = _extract_warning_default_value(loaded_parameter)
    return dcc.Textarea(
        id=page_ids.WARNING_CONTENT,
        className='form-control',
        value=default_value,
        style={'min-height': '300px'},
    )


def _warning_content_form(operation: AMOperation, loaded_parameter: Optional[ParameterObject]) -> Component:
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
    loaded_parameter: Optional[ParameterObject],
    destination_rank: int,
    text: StructuredText,
) -> Component:
    is_edition = destination_rank != -1
    fields = [
        _main_title(operation, is_edition=is_edition, rank=destination_rank),
        _get_delete_button(is_edition=is_edition),
        _get_source_form(operation, text_title_options, loaded_parameter),
        _get_target_section_block(operation, text_title_options, loaded_parameter, text, is_edition=is_edition),
        _warning_content_form(operation, loaded_parameter),
        _condition_form(operation, loaded_parameter),
    ]
    return html.Div(fields)


def _make_form(
    text_title_options: DropdownOptions,
    operation: AMOperation,
    parent_page: str,
    loaded_parameter: Optional[ParameterObject],
    destination_rank: int,
    text: StructuredText,
) -> Component:
    return html.Div(
        [
            _fields(text_title_options, operation, loaded_parameter, destination_rank, text),
            html.Div(id='param-edition-upsert-output', className='mt-2'),
            html.Div(id='param-edition-delete-output'),
            dcc.Store(id=page_ids.DROPDOWN_OPTIONS, data=json.dumps(text_title_options)),
            _buttons(parent_page),
        ]
    )


def _extract_reference_and_values_titles(text: StructuredText, path: Ints, level: int = 0) -> List[Tuple[str, str]]:
    return [(dump_path(path), get_truncated_str('#' * level + ' ' + text.title.text))] + [
        elt
        for rank, sec in enumerate(text.sections)
        for elt in _extract_reference_and_values_titles(sec, path + (rank,), level + 1)
    ]


def _extract_paragraph_reference_dropdown_values(text: StructuredText) -> DropdownOptions:
    title_references_and_values = _extract_reference_and_values_titles(text, ())
    return [{'label': title, 'value': reference} for reference, title in title_references_and_values]


def _get_instructions() -> Component:
    return html.Div(
        html.A(
            'Guide de paramétrage',
            href='https://www.notion.so/R-gles-de-param-trisation-47d8e5c4d3434d8691cbd9f59d556f0f',
            target='_blank',
        ),
        className='alert alert-light',
    )


def form(
    text: StructuredText,
    operation: AMOperation,
    parent_page: str,
    loaded_parameter: Optional[ParameterObject],
    destination_rank: int,
) -> Component:
    dropdown_values = _extract_paragraph_reference_dropdown_values(text)
    return html.Div(
        [
            _get_instructions(),
            _make_form(dropdown_values, operation, parent_page, loaded_parameter, destination_rank, text),
        ]
    )


def _handle_submit(
    operation: AMOperation,
    am_id: str,
    parameter_rank: int,
    source_str: str,
    target_section_form_values: TargetSectionFormValues,
    condition_form_values: ConditionFormValues,
    warning_content: str,
) -> Component:
    try:
        extract_and_upsert_new_parameter(
            operation,
            am_id,
            parameter_rank,
            source_str,
            target_section_form_values,
            condition_form_values,
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
            dcc.Location(pathname=build_am_page(am_id), id='param-edition-success-redirect'),
        ]
    )


def _deduce_parameter_object_type(operation: AMOperation) -> Type[ParameterObject]:
    if operation == AMOperation.ADD_ALTERNATIVE_SECTION:
        return AlternativeSection
    if operation == AMOperation.ADD_CONDITION:
        return InapplicableSection
    if operation == AMOperation.ADD_WARNING:
        return AMWarning
    raise NotImplementedError()


def _handle_delete(n_clicks: int, operation_str: str, am_id: str, parameter_rank: int) -> Component:
    if n_clicks == 0:
        return html.Div()
    try:
        operation = AMOperation(operation_str)
        DATA_FETCHER.remove_parameter(am_id, _deduce_parameter_object_type(operation), parameter_rank)
    except Exception:  # pylint: disable=broad-except
        return dbc.Alert(f'Unexpected error:\n{traceback.format_exc()}', color='danger')
    return html.Div(
        [
            dbc.Alert('Suppression réussie.', color='success'),
            dcc.Location(pathname=build_am_page(am_id), id='param-edition-success-redirect'),
        ]
    )


def _add_callbacks(app: dash.Dash):
    @app.callback(
        Output('param-edition-upsert-output', 'children'),
        Input('submit-val-param-edition', 'n_clicks'),
        State(page_ids.AM_OPERATION, 'children'),
        State(page_ids.AM_ID, 'children'),
        State(page_ids.PARAMETER_RANK, 'children'),
        State(page_ids.SOURCE, 'value'),
        State(page_ids.WARNING_CONTENT, 'value'),
        State(page_ids.new_text_title(cast(int, ALL)), 'value'),
        State(page_ids.new_text_content(cast(int, ALL)), 'value'),
        State(page_ids.target_section(cast(int, ALL)), 'value'),
        State(page_ids.target_alineas(cast(int, ALL)), 'value'),
        State(page_ids.condition_parameter(cast(int, ALL)), 'value'),
        State(page_ids.condition_operation(cast(int, ALL)), 'value'),
        State(page_ids.condition_value(cast(int, ALL)), 'value'),
        State(page_ids.CONDITION_MERGE, 'value'),
        prevent_initial_call=True,
    )
    def handle_submit(
        _,
        operation_str,
        am_id,
        parameter_rank,
        source_str,
        warning_content,
        new_texts_titles,
        new_texts_contents,
        target_sections,
        target_alineas,
        condition_parameters,
        condition_operations,
        condition_values,
        condition_merge,
    ):
        condition_form_values = ConditionFormValues(
            condition_parameters, condition_operations, condition_values, condition_merge
        )
        target_section_form_values = TargetSectionFormValues(
            new_texts_titles, new_texts_contents, target_sections, target_alineas
        )
        return _handle_submit(
            AMOperation(operation_str),
            am_id,
            parameter_rank,
            source_str,
            target_section_form_values,
            condition_form_values,
            warning_content,
        )

    @app.callback(
        Output('param-edition-delete-output', 'children'),
        Input('param-edition-delete-button', 'n_clicks'),
        State(page_ids.AM_OPERATION, 'children'),
        State(page_ids.AM_ID, 'children'),
        State(page_ids.PARAMETER_RANK, 'children'),
    )
    def handle_delete(n_clicks, operation, am_id, parameter_rank):
        return _handle_delete(n_clicks, operation, am_id, parameter_rank)

    @app.callback(
        Output(page_ids.TARGET_BLOCKS, 'children'),
        Input(page_ids.ADD_TARGET_BLOCK, 'n_clicks'),
        State(page_ids.TARGET_BLOCKS, 'children'),
        State(page_ids.AM_OPERATION, 'children'),
        State(page_ids.DROPDOWN_OPTIONS, 'data'),
        prevent_initial_call=True,
    )
    def add_block(n_clicks, children, operation_str, options_str):
        new_block = target_section_form(
            AMOperation(operation_str), json.loads(options_str), None, None, n_clicks + 1, False
        )
        return children + [new_block]


_add_callbacks(app)
