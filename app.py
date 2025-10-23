import re
from datetime import datetime, time
from io import BytesIO

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from core.crud import (add_turma, bootstrap_initial_user, check_password,
                       create_user, delete_turma, delete_user,
                       find_user_by_username, get_all_enrollments_by_semester,
                       get_all_turmas, get_all_users, get_configuracoes,
                       get_unique_semesters, update_configuracoes,
                       update_turma, update_user, delete_enrollment)
from core.database import get_database, get_db_connection
from utils.style import display_logo, load_css


def is_valid_semester_format(semester: str) -> bool:
    return re.fullmatch(r'\d{4}\.[0-9]', semester) is not None


def to_excel(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inscricoes')
    return output.getvalue()


def login_form(db):
    if st.session_state.get('logged_in', False):
        return True

    _, col2, _ = st.columns([1, 1.5, 1])

    with col2:
        with st.container(border=True):
            display_logo(st, class_name='login-logo')
            st.markdown(
                "<h2 style='text-align: center; margin-bottom: 20px;'>Painel de Administração</h2>",
                unsafe_allow_html=True,
            )

            with st.form('login_form'):
                username = st.text_input(
                    'Usuário', placeholder='Digite seu usuário'
                ).lower()
                password = st.text_input(
                    'Senha', type='password', placeholder='Digite sua senha'
                )
                submitted = st.form_submit_button(
                    'Login', width='stretch', type='primary'
                )

                if submitted:
                    user = find_user_by_username(db, username)
                    if user and check_password(
                        password, user['hashed_password']
                    ):
                        st.session_state.logged_in = True
                        st.session_state.username = user['username']
                        st.session_state.role = user['role']
                        st.rerun()
                    else:
                        st.error('Usuário ou senha incorretos.')
    return False


def display_user_management(db):
    st.title('👥 Gerenciamento de Usuários')
    user_role = st.session_state.get('role')
    if user_role not in ['admin-dev', 'admin']:
        st.error('🚫 Acesso Negado.')
        return

    with st.expander('➕ Adicionar Novo Usuário'):
        with st.form('new_user_form', clear_on_submit=True):
            username = st.text_input('Nome de Usuário')
            password = st.text_input('Senha', type='password')
            confirm_password = st.text_input(
                'Confirmar Senha', type='password'
            )
            role_options = (
                ['auxiliar', 'admin', 'admin-dev']
                if user_role == 'admin-dev'
                else ['auxiliar', 'admin']
            )
            role = st.selectbox('Nível de Acesso', role_options)

            if st.form_submit_button('Adicionar Usuário'):
                if password != confirm_password:
                    st.error('As senhas não coincidem.')
                elif find_user_by_username(db, username):
                    st.error('Este nome de usuário já existe.')
                else:
                    create_user(
                        db,
                        {
                            'username': username,
                            'password': password,
                            'role': role,
                        },
                    )
                    st.success(f"Usuário '{username}' criado com sucesso!")
                    st.rerun()

    st.subheader('Usuários Cadastrados')
    users = get_all_users(db, admin_dev=(user_role == 'admin-dev'))

    for user in users:
        st.markdown('---')
        cols = st.columns([3, 2, 1, 1])
        cols[0].write(f"**Usuário:** {user['username']}")
        cols[1].write(f"**Nível:** `{user['role']}`")

        if cols[2].button(
            '✏️', key=f"edit_{user['_id']}", help='Editar Usuário'
        ):
            st.session_state.edit_user_id = user['_id']
        if cols[3].button(
            '🗑️', key=f"delete_{user['_id']}", help='Deletar Usuário'
        ):
            delete_user(db, user['_id'])
            st.rerun()

        if st.session_state.get('edit_user_id') == user['_id']:
            with st.form(f"edit_form_{user['_id']}"):
                st.write(f"Editando **{user['username']}**")
                new_username = st.text_input(
                    'Novo Nome de Usuário', value=user['username']
                )
                new_password = st.text_input(
                    'Nova Senha (deixe em branco para não alterar)',
                    type='password',
                )
                confirm_new_password = st.text_input(
                    'Confirmar Nova Senha', type='password'
                )
                roles = (
                    ['auxiliar', 'admin', 'admin-dev']
                    if user_role == 'admin-dev'
                    else ['auxiliar', 'admin']
                )
                new_role = st.selectbox(
                    'Nível', roles, index=roles.index(user['role'])
                )

                col_save, col_cancel = st.columns(2)
                if col_save.form_submit_button('Salvar'):
                    if new_password != confirm_new_password:
                        st.error('As novas senhas não coincidem.')
                    else:
                        try:
                            update_data = {
                                'username': new_username,
                                'role': new_role,
                            }
                            if new_password:
                                update_data['password'] = new_password
                            update_user(db, user['_id'], update_data)
                            del st.session_state.edit_user_id
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                if col_cancel.form_submit_button('Cancelar'):
                    del st.session_state.edit_user_id
                    st.rerun()


def display_enrollment_management(db, config):
    st.title('🧑‍🎓 Gerenciamento de Inscrições')
    active_semester = config.get('activeSemester', 'N/A')
    st.markdown(
        f'Visualizando inscrições para o semestre **{active_semester}**.'
    )
    enrollments = get_all_enrollments_by_semester(db, active_semester)
    if not enrollments:
        st.warning('Nenhuma inscrição encontrada.')
        return
    df = pd.DataFrame(enrollments)
    df['nota_classificacao'] = df.get(
        'notas_relevantes', pd.Series(dtype='object')
    ).apply(lambda x: x.get('nota_predita', 0) if isinstance(x, dict) else 0)
    st.subheader('Pesquisar e Filtrar')
    search_query = st.text_input(
        'Pesquisar por Nome, Matrícula, etc.',
        placeholder='Digite aqui para buscar...',
    )
    filtered_df = df.copy()
    if search_query:
        search_query = search_query.lower()
        filtered_df = df[
            df.apply(lambda row: search_query in str(row).lower(), axis=1)
        ]
    display_columns = [
        'Nome',
        'Matricula',
        'Curso',
        'turma_escolhida',
        'escolha',
        'nota_classificacao',
        'data_inscricao',
    ]
    st.dataframe(
        filtered_df[display_columns], width='stretch', hide_index=True
    )
    st.info(f'Exibindo **{len(filtered_df)}** de **{len(df)}** inscrições.')
    excel_data = to_excel(filtered_df)
    st.download_button(
        '📥 Exportar para Excel',
        excel_data,
        f'inscricoes_{active_semester}.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        width='stretch',
    )

    user_role = st.session_state.get('role', 'auxiliar')
    can_delete = user_role in ['admin-dev', 'admin']

    if can_delete:
        display_columns = [
        'Nome',
        'Matricula',
        'Curso',
        'turma_escolhida',
        'escolha',
        'nota_classificacao',
        'data_inscricao',
        ]

        with st.expander('✏️ Gerenciar e Excluir Inscrições', expanded=False):
            st.markdown('### Lista Interativa')

            col_widths = [2, 1.5, 1, 1, 0.7 if can_delete else 0.1]

            cols_header = st.columns(col_widths)
            cols_header[0].markdown('**Nome**')
            cols_header[1].markdown('**Matrícula**')
            cols_header[2].markdown('**Turma Escolhida**')
            cols_header[3].markdown('**Nota**')
            cols_header[4].markdown('**Ação**')

            filtered_enrollments_list = filtered_df.to_dict('records')

            for enrollment in filtered_enrollments_list:
                st.markdown('---')
                cols = st.columns(col_widths)

                enrollment_id = enrollment['_id']

                cols[0].write(enrollment.get('Nome', 'N/A'))
                cols[1].write(enrollment.get('Matricula', 'N/A'))
                cols[2].write(enrollment.get('turma_escolhida', 'N/A'))
                cols[3].write(f"{enrollment.get('nota_classificacao', 0):.2f}")

                if cols[4].button(
                    '🗑️',
                    key=f"delete_enrollment_{enrollment_id}",
                    help=f"Excluir inscrição de {enrollment.get('Nome')}",
                ):
                    delete_enrollment(db, enrollment_id)
                    st.success(f"Inscrição de {enrollment.get('Nome')} excluída com sucesso!")
                    st.rerun()


def display_turma_management(db, config):
    st.title('📚 Gerenciamento de Turmas')
    user_role = st.session_state.get('role', 'auxiliar')
    with st.expander('➕ Adicionar Nova Turma'):
        with st.form('new_turma_form', clear_on_submit=True):
            name = st.text_input('Nome da Turma')
            semester = st.text_input(
                'Semestre', help='Formato `AAAA.1` ou `AAAA.2`'
            )
            is_active = st.checkbox('Ativa?', value=True)
            submit_button = st.form_submit_button('Adicionar Turma')
            if submit_button:
                if name and is_valid_semester_format(semester):
                    add_turma(
                        db,
                        {
                            'name': name,
                            'semester': semester,
                            'is_active': is_active,
                        },
                    )
                    st.success(f"Turma '{name}' adicionada!")
                    st.rerun()
                else:
                    st.error(
                        'Formato de semestre inválido(Ex: 2023.1) ou nome vazio.'
                    )
    st.subheader('Filtros e Visualização')
    all_semesters = sorted(get_unique_semesters(db), reverse=True)
    active_semester = config.get('activeSemester')
    try:
        default_index = all_semesters.index(active_semester)
    except (ValueError, TypeError):
        default_index = 0
    col1, col2 = st.columns(2)
    selected_semester = col1.selectbox(
        'Filtrar por Semestre', all_semesters, index=default_index
    )
    status_filter = col2.radio(
        'Filtrar por Status', ['Ativas', 'Inativas', 'Todas'], horizontal=True
    )
    turmas = get_all_turmas(db)
    filtered_turmas = [
        t for t in turmas if t.get('semester') == selected_semester
    ]
    if status_filter == 'Ativas':
        filtered_turmas = [t for t in filtered_turmas if t.get('is_active')]
    elif status_filter == 'Inativas':
        filtered_turmas = [
            t for t in filtered_turmas if not t.get('is_active')
        ]
    if not filtered_turmas:
        st.info('Nenhuma turma encontrada.')
        return
    for turma in filtered_turmas:
        st.markdown('---')
        can_delete = user_role in ['admin-dev', 'admin']
        cols = (
            st.columns([1, 6, 1, 1]) if can_delete else st.columns([1, 7, 1])
        )
        status_icon = '✅' if turma.get('is_active') else '❌'
        cols[0].write(status_icon)
        cols[1].write(
            f"**{turma.get('name')}** (Sem.: {turma.get('semester')})"
        )
        if cols[2].button(
            '✏️', key=f"edit_{turma['_id']}", help='Editar Turma'
        ):
            st.session_state.edit_turma_id = turma['_id']
        if can_delete:
            if cols[3].button(
                '🗑️', key=f"delete_{turma['_id']}", help='Deletar Turma'
            ):
                delete_turma(db, turma['_id'])
                st.rerun()
        if st.session_state.get('edit_turma_id') == turma['_id']:
            with st.form(f"edit_form_{turma['_id']}"):
                new_name = st.text_input('Nome', value=turma.get('name'))
                new_semester = st.text_input(
                    'Semestre', value=turma.get('semester')
                )
                new_is_active = st.checkbox(
                    'Ativa', value=turma.get('is_active')
                )
                col_save, col_cancel = st.columns(2)
                if col_save.form_submit_button('Salvar'):
                    if is_valid_semester_format(new_semester):
                        update_turma(
                            db,
                            turma['_id'],
                            {
                                'name': new_name,
                                'semester': new_semester,
                                'is_active': new_is_active,
                            },
                        )
                        del st.session_state.edit_turma_id
                        st.rerun()
                    else:
                        st.error('Formato inválido.')
                if col_cancel.form_submit_button('Cancelar'):
                    del st.session_state.edit_turma_id
                    st.rerun()


def display_settings_management(db, config):
    st.title('⚙️ Configurações do Sistema')
    user_role = st.session_state.get('role')
    if user_role not in ['admin-dev', 'admin']:
        st.error('🚫 Acesso Negado.')
        return
    with st.form(key='config_form'):
        st.subheader('Período de Inscrição')
        active_semester = st.text_input(
            'Semestre Ativo',
            value=config.get('activeSemester', ''),
            help='Formato `AAAA.1` ou `AAAA.2`',
        )
        current_start = (
            pd.to_datetime(config.get('enrollmentStartDate')).to_pydatetime()
            if config.get('enrollmentStartDate')
            else datetime.now()
        )
        current_end = (
            pd.to_datetime(config.get('enrollmentEndDate')).to_pydatetime()
            if config.get('enrollmentEndDate')
            else datetime.now()
        )
        col1, col2 = st.columns(2)
        start_date = col1.date_input(
            'Data de Início', value=current_start.date()
        )
        start_time = col2.time_input(
            'Hora de Início', value=current_start.time()
        )
        col3, col4 = st.columns(2)
        end_date = col3.date_input('Data de Término', value=current_end.date())
        end_time = col4.time_input('Hora de Término', value=current_end.time())
        st.subheader('Regras de Negócio')
        cutoff_score = st.number_input(
            'Nota de Corte',
            value=float(config.get('cutoffScore', 6.75)),
            format='%.2f',
        )
        submit_button = st.form_submit_button(
            '💾 Salvar', width='stretch', type='primary'
        )
    if submit_button:
        if is_valid_semester_format(active_semester):
            final_start_datetime = datetime.combine(start_date, start_time)
            final_end_datetime = datetime.combine(end_date, end_time)
            new_config = {
                'activeSemester': active_semester,
                'enrollmentStartDate': pd.to_datetime(
                    final_start_datetime, utc=True
                ).isoformat(),
                'enrollmentEndDate': pd.to_datetime(
                    final_end_datetime, utc=True
                ).isoformat(),
                'cutoffScore': cutoff_score,
            }
            if update_configuracoes(db, new_config):
                st.success('Salvo!')
                st.rerun()
            else:
                st.error('Erro ao salvar.')
        else:
            st.error('Formato de Semestre inválido!')


def main():
    st.set_page_config(
        page_title='Admin | Verificalp', page_icon='⚙️', layout='wide'
    )
    load_css()

    client = get_db_connection()
    db = get_database(client)
    if db is None:
        st.error('Falha na conexão com o banco de dados.')
        st.stop()

    bootstrap_initial_user(db, st.secrets.get('bootstrap_user', {}))

    if not login_form(db):
        st.stop()

    config = get_configuracoes(db)
    user_role = st.session_state.get('role')

    with st.sidebar:
        display_logo(st.sidebar, class_name='sidebar-logo')
        st.sidebar.write(f"Usuário: **{st.session_state.get('username')}**")
        st.sidebar.write(f'Nível: **{user_role}**')
        if st.sidebar.button('Logout', width='stretch'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        menu_options = ['Inscrições', 'Turmas']
        menu_icons = ['person-lines-fill', 'collection']
        if user_role in ['admin-dev', 'admin']:
            menu_options.extend(['Usuários', 'Configurações'])
            menu_icons.extend(['people-fill', 'gear'])

        selected = option_menu(
            menu_title='Painel de Controle',
            options=menu_options,
            icons=menu_icons,
            default_index=0,
        )

    if selected == 'Inscrições':
        display_enrollment_management(db, config)
    elif selected == 'Turmas':
        display_turma_management(db, config)
    elif selected == 'Usuários' and user_role in ['admin-dev', 'admin']:
        display_user_management(db)
    elif selected == 'Configurações' and user_role in ['admin-dev', 'admin']:
        display_settings_management(db, config)


if __name__ == '__main__':
    main()
