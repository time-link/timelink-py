from nicegui import app, ui

from timelink.linking import service as linking
from timelink.web.pages import navbar


class Linking:

    """Page for managing existing links and real entities (Entity Resolution).

    Mirrors MHK ``linking_show.vm``: list the real entities identified in
    the database, optionally filtered by user, with their occurrences;
    occurrences can be visited or unlinked. This page does not run
    automatic linking — it only manages links that already exist.
    """

    def __init__(self, timelink_app) -> None:
        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server

        @ui.page('/linking')
        async def register():
            await self.linking_page()

    async def linking_page(self):
        # unique login identity (nickname), never the non-unique display name
        current_user = (
            app.storage.user.get('nickname') or app.storage.user.get('username', 'guest')
        )

        with navbar.header():
            ui.page_title("Linking")
            ui.markdown('#### **Linking, Entity Resolution and Linked Data**').classes('ml-2 mb-4 text-orange-500')

            user_filter = ui.input(
                'Filter by user (empty = all users)', value=current_user
            ).classes('w-64')

            @ui.refreshable
            def render_rentities():
                with self.database.session() as session:
                    rentities = linking.list_rentities(
                        session, user=user_filter.value or None)

                if not rentities:
                    ui.label('No real entities found for this user.').classes('text-gray-500')
                    return

                columns = [
                    {'name': 'rid', 'label': 'Real entity', 'field': 'rid', 'align': 'left'},
                    {'name': 'user', 'label': 'User', 'field': 'user', 'align': 'left'},
                    {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'left'},
                    {'name': 'n', 'label': 'Occurrences', 'field': 'n_occurrences', 'align': 'left'},
                ]
                rows = [
                    {'rid': r['rid'], 'user': r['user'],
                     'status': r['status'], 'n_occurrences': r['n_occurrences']}
                    for r in rentities
                ]
                table = ui.table(columns=columns, rows=rows, row_key='rid').classes('w-full')
                table.add_slot('body-cell-rid', '''
                    <q-td :props="props">
                        <a :href="'/id/' + props.row.rid" class="text-blue-600">
                            {{ props.row.rid }}</a>
                    </q-td>
                ''')

                for r in rentities:
                    self._render_occurrences(r['rid'], current_user)

            def refresh():
                render_rentities.refresh()

            user_filter.on('keydown.enter', refresh)
            ui.button('Refresh', on_click=refresh).props('icon=refresh')

            render_rentities()

    def _render_occurrences(self, rid: str, current_user: str):
        """Expansible list of occurrences linked to one real entity."""
        with self.database.session() as session:
            links = linking.rentity_links(session, rid)

        with ui.expansion(f'{rid} — {len(links)} occurrence(s)',
                          icon='link').classes('w-full'):
            columns = [
                {'name': 'entity', 'label': 'Occurrence', 'field': 'entity', 'align': 'left'},
                {'name': 'class', 'label': 'Class', 'field': 'class', 'align': 'left'},
                {'name': 'user', 'label': 'Linked by', 'field': 'user', 'align': 'left'},
                {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'left'},
                {'name': 'actions', 'label': '', 'field': 'actions'},
            ]
            rows = [
                {k: link[k] for k in ('entity', 'class', 'user', 'status')}
                | {'own': link['user'] == current_user}
                for link in links
            ]

            def unlink(entity_id, rid=rid, by_user=current_user):
                # expected_rid: the server re-checks that this user's link
                # really belongs to the rid being displayed
                with self.database.session() as session:
                    try:
                        linking.unlink_occurrence(
                            entity_id, by_user, session, expected_rid=rid)
                    except ValueError as e:
                        ui.notify(f'Refused: {e}', type='negative')
                        return
                ui.notify(f'Unlinked {entity_id} from {rid}')
                ui.navigate.to('/linking')

            table = ui.table(columns=columns, rows=rows, row_key='entity').classes('w-full')
            table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn dense flat icon="open_in_new"
                        :href="'/id/' + props.row.entity" />
                    <q-btn v-if="props.row.own"
                        dense flat icon="link_off" color="negative"
                        @click="$parent.$emit('unlink', props.row)" />
                </q-td>
            ''')
            table.on('unlink', lambda e: unlink(e.args['entity']))
