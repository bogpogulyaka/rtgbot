import asyncio
import logging
import math
import typing as tp

import rtgbot.components.widgets
from rtgbot.base import ComponentTreeNode
from rtgbot.components.base import WindowsGroup
from rtgbot.etities.dom import DOMMessageUpdate, RenderContext, DOM


class Renderer:
    def __init__(self, context: RenderContext):
        self.context = context

        self.component_tree: tp.Optional[WindowsGroup] = None
        self.dom: DOM = []

        self.render_cycle_id = 0

    async def render(self, updated_nodes: tp.List[ComponentTreeNode], force_update_node: ComponentTreeNode = None):
        modified_trees = []

        # collect modified trees
        for node in updated_nodes:
            if not node.is_visible:
                continue

            is_top = True
            parent_node = node
            while parent_node:
                parent_node = parent_node._render_data.parent
                if parent_node in updated_nodes:
                    is_top = False
                    break
            if is_top:
                modified_trees.append(node)

        async with asyncio.TaskGroup() as tg:
            for node in modified_trees:
                tg.create_task(self.render_tree(node))

        return await self.render_dom(force_update_node)

    async def render_tree(self, updated_node: ComponentTreeNode):
        if updated_node._render_data.parent is None:
            self.component_tree = await self._render_node(updated_node, self.component_tree)
        else:
            parent_node = updated_node._render_data.parent
            children = parent_node._render_data.children

            prev_node_key = list(children.keys())[list(children.values()).index(updated_node)]

            children[prev_node_key] = await self._render_node(updated_node, updated_node)
            parent_node._render_data.children_visible = self._filter_visible_children(children)

        self.render_cycle_id += 1
        self.context.render_cycle_id = self.render_cycle_id

    async def _render_node(self, node: ComponentTreeNode, prev_node: ComponentTreeNode = None) -> ComponentTreeNode:
        created = prev_node is None

        updated_props = {}

        if created:
            rendered_node = node
            updated_props = rendered_node._props
        else:
            rendered_node = prev_node

            # record updated props
            for key, value in node._props.items():
                prev_value = rendered_node._props[key]

                if key != 'children' and prev_value != value:
                    updated_props[key] = (value, prev_value)

            rendered_node._props = node._props

        rendered_node._context = self.context
        rendered_node._render_data.render_cycle_id = self.render_cycle_id
        rendered_node._is_dirty = False

        # return previous version if not visible
        if not rendered_node.props.visible:
            return rendered_node

        # lock node notifications
        rendered_node._can_push_notifications = False

        # handle props updates
        for k, v in updated_props.items():
            if k == 'children':
                continue

            if created:
                value = v
                prev_value = None
            else:
                value, prev_value = v

            rendered_node.rct._set_value(k, value, True)
            # logging.info(f"prop {k}: {prev_value} -> {value}")

        try:
            if created:
                await rendered_node.setup()
                await rendered_node.before_mount()
            else:
                await rendered_node.before_update()

            # render node
            children = await rendered_node.render()

            # unlock node notifications
            rendered_node._can_push_notifications = True
            if created:
                rendered_node.rct._reset_state_history()

            # convert to tuple
            if not isinstance(children, tp.Tuple):
                children = children,

            # render children
            tg = []
            for index, child in enumerate(children):
                tg.append(asyncio.create_task(self._render_child(child, index, prev_node)))
            children_render_result = await asyncio.gather(*tg)

            # collect result
            rendered_children = {}

            for child_result in children_render_result:
                child, key = child_result
                if child:
                    child._render_data.parent = rendered_node
                    child._render_data.set_key(key)

                    rendered_children[key] = child

            # unmount deleted child nodes
            if prev_node:
                for key, child in prev_node._render_data.children.items():
                    if key not in rendered_children:
                        await self._unmount_recursive(child)

            rendered_node._render_data.children = rendered_children
            rendered_node._render_data.children_visible = self._filter_visible_children(rendered_children)

            if created:
                await rendered_node.mounted()
            else:
                await rendered_node.updated()

            # call activated/deactivated hooks
            is_visible = rendered_node.props.visible
            if prev_node is None or is_visible != prev_node.props.visible:
                await self._visibility_recursive(rendered_node, is_visible)

            return rendered_node
        except Exception as e:
            logging.exception("Exception occurred while rendering component:")

            children = {"exception": rtgbot.components.widgets.ExceptionComponent(e)}
            rendered_node._render_data.children = children
            rendered_node._render_data.children_visible = children

            # unlock node notifications
            rendered_node._can_push_notifications = True
            if created:
                rendered_node.rct._reset_state_history()

            return rendered_node

    async def _render_child(self, child, index, prev_parent_node):
        # if isinstance(child, tp.Tuple):
        #     child = ComponentTreeNode()(*child)

        # filter when False
        if child.props.when is False:
            return None, None

        # create key
        key = index
        if child.props.key is not None:
            key = child.props.key

        # match node from previous iteration
        prev_child = None
        if prev_parent_node and key in prev_parent_node._render_data.children:
            match = prev_parent_node._render_data.children[key]
            if type(match) == type(child):
                prev_child = match

        return await self._render_node(child, prev_child), key

    async def _unmount_recursive(self, node: ComponentTreeNode):
        await node.before_unmount()

        for child in node._render_data.children.values():
            await self._unmount_recursive(child)

        node._render_data.children.clear()
        node._render_data.children_visible.clear()

        await node.unmounted()

    async def _visibility_recursive(self, node: ComponentTreeNode, visibility: bool):
        for child in node._render_data.children.values():
            await self._visibility_recursive(child, visibility)

        if visibility:
            await node.activated()
        else:
            await node.deactivated()

    def _filter_visible_children(self, nodes):
        return dict(filter(lambda item: item[1].props.visible, nodes.items()))

    async def render_dom(self, force_update_node: ComponentTreeNode):
        dom = self.dom
        new_dom = self.component_tree.render_messages()

        # find force update message node
        dom_dict = {}
        for message in dom:
            dom_dict[message.key] = message

        while force_update_node is not None and force_update_node.rendered_chained_key not in dom_dict:
            force_update_node = force_update_node._render_data.parent

        force_update_node_key = None
        if force_update_node is not None:
            force_update_node_key = force_update_node.rendered_chained_key

        actions = self._calculate_dom_edit_actions(dom, new_dom, force_update_node_key)
        # logging.info(actions)

        dom_update = []
        for action in actions:
            a, id_from, id_to = action
            old_message = len(dom) > 0 and dom[id_from] or None
            new_message = len(new_dom) > 0 and new_dom[id_to] or None

            actions = [
                DOMMessageUpdate.Action.keep,
                DOMMessageUpdate.Action.update,
                DOMMessageUpdate.Action.delete,
                DOMMessageUpdate.Action.send
            ]

            dom_update.append(DOMMessageUpdate(
                action=actions[a + 1],
                old_message=old_message,
                new_message=new_message
            ))

        self.dom = new_dom
        return self.dom, dom_update

    def _calculate_dom_edit_actions(self, m1: tp.List, m2: tp.List, force_update_message_key: str):
        send_cost_mult = 2
        edit_cost_mult = 1.5
        delete_cost = 0.5

        l1 = len(m1)
        l2 = len(m2)

        d = [[(0., 0., 0., 0.)] * (l1 + 1) for _ in range(l2 + 1)]
        d[-1][-1] = 0, math.inf, 2, 2

        # init send
        for i in range(0, l2):
            d[i][-1] = d[i - 1][-1][0] + send_cost_mult * m2[i].send_cost, math.inf, 2, 2
        # init delete
        for j in range(-1, l1):
            d[-1][j] = (j + 1) * delete_cost, (j + 1) * delete_cost, 1, 1

        for i in range(l2):
            m_to = m2[i]
            m_send_cost = m_to.send_cost
            send_cost = m_send_cost * send_cost_mult

            for j in range(l1):
                m_from = m1[j]
                if m_from.can_edit(m_to):
                    edit_cost = m_from.edit_cost(m_to) * edit_cost_mult
                else:
                    edit_cost = math.inf

                if m_from.key == force_update_message_key and edit_cost == 0:
                    edit_cost = 1

                # send streak
                costs1 = [
                    d[i - 1][j - 1][1] + edit_cost,  # update
                    min(d[i][j - 1][0], d[i][j - 1][1]) + delete_cost,  # delete
                    min(d[i - 1][j][0], d[i - 1][j][1]) + send_cost,  # send
                ]

                # without send
                costs2 = [
                    d[i - 1][j - 1][1] + edit_cost,  # update
                    d[i][j - 1][1] + delete_cost,  # delete
                ]

                min_cost1, action1 = math.inf, 0
                for k, c in enumerate(costs1):
                    if c < min_cost1:
                        min_cost1, action1 = c, k

                min_cost2, action2 = math.inf, 0
                for k, c in enumerate(costs2):
                    if c < min_cost2:
                        min_cost2, action2 = c, k

                d[i][j] = min_cost1, min_cost2, action1, action2

        actions = []

        i, j = l2 - 1, l1 - 1
        prev_cost = math.inf
        min_cost = 0
        has_update = False

        while i >= 0 or j >= 0:
            min_cost1, min_cost2, action1, action2 = d[i][j]

            min_cost = min_cost2
            action = action2
            if not has_update and min_cost1 < min_cost2:
                min_cost = min_cost1
                action = action1

            if len(actions) > 0 and min_cost == prev_cost:
                a = actions[-1]
                actions[-1] = (-1, a[1], a[2])
            actions.append((action, j, i))

            if action == 0:
                has_update = True
                i -= 1
                j -= 1
            elif action == 1:
                j -= 1
            else:
                i -= 1

            prev_cost = min_cost

        if min_cost == 0:
            a = actions[-1]
            actions[-1] = (-1, a[1], a[2])
        actions.reverse()

        return actions
