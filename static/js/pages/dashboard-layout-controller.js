(function() {
  function createDashboardLayoutController(options) {
    var layoutRoot = options.layoutRoot;
    var toolbar = options.toolbar;
    var workspace = options.workspace;
    var hiddenPool = options.hiddenPool;
    var hiddenList = options.hiddenList;
    var toggleButton = options.toggleButton;
    var resetButton = options.resetButton;
    var statusNode = options.statusNode;
    var saveUrl = options.saveUrl;
    var isEditing = false;
    var draggedPanel = null;
    var dragHandlePressed = false;

    function getCookie(name) {
      var value = '; ' + document.cookie;
      var parts = value.split('; ' + name + '=');
      if (parts.length === 2) {
        return parts.pop().split(';').shift();
      }
      return '';
    }

    function setStatus(message) {
      if (!statusNode) {
        return;
      }
      statusNode.classList.remove('visually-hidden');
      statusNode.textContent = message;
    }

    function getPanels() {
      return Array.from(layoutRoot.querySelectorAll('[data-panel-id]'));
    }

    function getSlotContainers() {
      return Array.from(workspace.querySelectorAll('[data-dashboard-slot-id]'));
    }

    function serializeLayout() {
      var state = {};
      getSlotContainers().forEach(function(slot) {
        var slotId = slot.dataset.dashboardSlotId || slot.dataset.dashboardSlot;
        state[slotId] = Array.from(slot.children).filter(function(panel) {
          return panel.hasAttribute('data-panel-id');
        }).map(function(panel) {
          return panel.dataset.panelId;
        });
      });
      return state;
    }

    function serializeCollapsedBlocks() {
      return getPanels().filter(function(panel) {
        return panel.dataset.dashboardHidden !== 'true' && panel.dataset.dashboardCollapsed === 'true';
      }).map(function(panel) {
        return panel.dataset.panelId;
      });
    }

    function serializeHiddenBlocks() {
      return getPanels().filter(function(panel) {
        return panel.dataset.dashboardHidden === 'true';
      }).map(function(panel) {
        return panel.dataset.panelId;
      });
    }

    function rebuildHiddenTray() {
      if (!hiddenList) {
        return;
      }

      var hiddenPanels = getPanels().filter(function(panel) {
        return panel.dataset.dashboardHidden === 'true';
      });

      hiddenList.innerHTML = '';
      if (!hiddenPanels.length) {
        hiddenList.innerHTML = '<p class="dashboard-layout-hidden-empty" data-dashboard-hidden-empty>Nenhum bloco oculto.</p>';
        if (toolbar) {
          toolbar.classList.remove('has-hidden-blocks');
        }
        return;
      }

      hiddenPanels.forEach(function(panel) {
        var button = document.createElement('button');
        button.className = 'button secondary dashboard-layout-hidden-chip';
        button.type = 'button';
        button.dataset.restoreBlock = panel.dataset.panelId;
        button.textContent = 'Restaurar ' + (panel.dataset.dashboardLabel || panel.dataset.panelId);
        hiddenList.appendChild(button);
      });

      if (toolbar) {
        toolbar.classList.add('has-hidden-blocks');
      }
    }

    function refreshPanelControls(panel) {
      var isHidden = panel.dataset.dashboardHidden === 'true';
      var currentSlot = panel.dataset.dashboardCurrentSlot;
      Array.from(panel.querySelectorAll('[data-move-slot]')).forEach(function(button) {
        button.hidden = button.dataset.moveSlot === currentSlot;
      });

      var collapseButton = panel.querySelector('[data-toggle-collapse]');
      if (collapseButton) {
        var isCollapsed = panel.dataset.dashboardCollapsed === 'true';
        collapseButton.textContent = isCollapsed ? 'Expandir' : 'Recolher';
        collapseButton.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
        collapseButton.hidden = isHidden;
      }

      var hideButton = panel.querySelector('[data-hide-block]');
      if (hideButton) {
        hideButton.hidden = isHidden;
      }
    }

    function refreshAllControls() {
      getPanels().forEach(refreshPanelControls);
    }

    function applyLayoutState(layoutState) {
      if (!layoutState || !layoutState.slots) {
        return;
      }

      var collapsedBlocks = Array.isArray(layoutState.collapsed_blocks) ? layoutState.collapsed_blocks : [];
      var hiddenBlocks = Array.isArray(layoutState.hidden_blocks) ? layoutState.hidden_blocks : [];

      getPanels().forEach(function(panel) {
        var isHidden = hiddenBlocks.indexOf(panel.dataset.panelId) >= 0;
        panel.dataset.dashboardHidden = isHidden ? 'true' : 'false';
        panel.classList.toggle('is-hidden', isHidden);
        if (isHidden && hiddenPool) {
          panel.dataset.dashboardCollapsed = 'false';
          panel.classList.remove('is-collapsed');
          hiddenPool.appendChild(panel);
        }
      });

      Object.keys(layoutState.slots).forEach(function(slotId) {
        var slot = workspace.querySelector('[data-dashboard-slot-id="' + slotId + '"]');
        if (!slot) {
          return;
        }

        layoutState.slots[slotId].forEach(function(blockId) {
          var panel = workspace.querySelector('[data-panel-id="' + blockId + '"]');
          if (!panel && hiddenPool) {
            panel = hiddenPool.querySelector('[data-panel-id="' + blockId + '"]');
          }
          if (!panel) {
            return;
          }
          slot.appendChild(panel);
          panel.dataset.dashboardCurrentSlot = slotId;
          panel.dataset.dashboardHidden = 'false';
          panel.classList.remove('is-hidden');
        });
      });

      getPanels().forEach(function(panel) {
        if (panel.dataset.dashboardHidden === 'true') {
          panel.dataset.dashboardCollapsed = 'false';
          panel.classList.remove('is-collapsed');
          return;
        }
        var isCollapsed = collapsedBlocks.indexOf(panel.dataset.panelId) >= 0;
        panel.dataset.dashboardCollapsed = isCollapsed ? 'true' : 'false';
        panel.classList.toggle('is-collapsed', isCollapsed);
      });

      rebuildHiddenTray();
      refreshAllControls();
    }

    function persistLayout(payload, successMessage) {
      setStatus('Salvando layout...');
      return fetch(saveUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(payload)
      }).then(function(response) {
        return response.json().then(function(data) {
          return { ok: response.ok, data: data };
        });
      }).then(function(result) {
        if (!result.ok || !result.data.ok) {
          throw new Error(result.data.error || 'save-failed');
        }
        applyLayoutState(result.data.layout);
        setStatus(successMessage);
      }).catch(function() {
        setStatus('Nao consegui salvar o layout agora.');
      });
    }

    function persistCurrentState(successMessage) {
      return persistLayout(
        {
          slots: serializeLayout(),
          collapsed_blocks: serializeCollapsedBlocks(),
          hidden_blocks: serializeHiddenBlocks(),
        },
        successMessage
      );
    }

    function getDragAfterElement(container, clientY) {
      var panels = Array.from(container.children).filter(function(panel) {
        return panel.hasAttribute('data-panel-id') && !panel.classList.contains('is-dragging');
      });

      return panels.reduce(function(closest, panel) {
        var box = panel.getBoundingClientRect();
        var offset = clientY - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset: offset, element: panel };
        }
        return closest;
      }, { offset: Number.NEGATIVE_INFINITY, element: null }).element;
    }

    function movePanelToSlot(panel, slotId) {
      var slot = workspace.querySelector('[data-dashboard-slot-id="' + slotId + '"]');
      if (!slot) {
        return;
      }
      slot.appendChild(panel);
      panel.dataset.dashboardCurrentSlot = slotId;
      refreshPanelControls(panel);
      persistCurrentState('Layout salvo.');
    }

    function toggleEditing() {
      isEditing = !isEditing;
      workspace.classList.toggle('is-layout-editing', isEditing);
      if (toolbar) {
        toolbar.classList.toggle('is-layout-editing', isEditing);
      }
      toggleButton.setAttribute('aria-pressed', isEditing ? 'true' : 'false');
      toggleButton.textContent = isEditing ? 'Fechar organizacao' : 'Organizar painel';
      setStatus(isEditing ? 'Modo de organizacao ativo.' : 'Modo de organizacao fechado.');
    }

    function resetLayout() {
      persistLayout({ reset: true }, 'Layout restaurado para o padrao.');
    }

    function handleWorkspaceClick(event) {
      var hideButton = event.target.closest('[data-hide-block]');
      if (hideButton) {
        var hiddenPanel = hideButton.closest('[data-panel-id]');
        if (!hiddenPanel || !hiddenPool) {
          return;
        }
        hiddenPanel.dataset.dashboardHidden = 'true';
        hiddenPanel.dataset.dashboardCollapsed = 'false';
        hiddenPanel.classList.remove('is-collapsed');
        hiddenPanel.classList.add('is-hidden');
        hiddenPool.appendChild(hiddenPanel);
        rebuildHiddenTray();
        refreshPanelControls(hiddenPanel);
        persistCurrentState('Bloco ocultado.');
        return;
      }

      var directionButton = event.target.closest('[data-move-direction]');
      if (directionButton) {
        var directionPanel = directionButton.closest('[data-panel-id]');
        if (!directionPanel) {
          return;
        }
        if (directionButton.dataset.moveDirection === 'up' && directionPanel.previousElementSibling) {
          directionPanel.parentElement.insertBefore(directionPanel, directionPanel.previousElementSibling);
        }
        if (directionButton.dataset.moveDirection === 'down' && directionPanel.nextElementSibling) {
          directionPanel.parentElement.insertBefore(directionPanel.nextElementSibling, directionPanel);
        }
        persistCurrentState('Layout salvo.');
        return;
      }

      var collapseButton = event.target.closest('[data-toggle-collapse]');
      if (collapseButton) {
        var collapsePanel = collapseButton.closest('[data-panel-id]');
        if (!collapsePanel) {
          return;
        }
        var isCollapsed = collapsePanel.dataset.dashboardCollapsed === 'true';
        collapsePanel.dataset.dashboardCollapsed = isCollapsed ? 'false' : 'true';
        collapsePanel.classList.toggle('is-collapsed', !isCollapsed);
        refreshPanelControls(collapsePanel);
        persistCurrentState('Estado do bloco salvo.');
        return;
      }

      var moveSlotButton = event.target.closest('[data-move-slot]');
      if (moveSlotButton) {
        var panel = moveSlotButton.closest('[data-panel-id]');
        if (!panel) {
          return;
        }
        movePanelToSlot(panel, moveSlotButton.dataset.moveSlot);
      }
    }

    function handleRootClick(event) {
      var restoreButton = event.target.closest('[data-restore-block]');
      if (!restoreButton) {
        return;
      }

      var panel = layoutRoot.querySelector('[data-panel-id="' + restoreButton.dataset.restoreBlock + '"]');
      if (!panel) {
        return;
      }

      var allowedSlots = (panel.dataset.dashboardAllowedSlots || '').split(',').filter(Boolean);
      var targetSlotId = panel.dataset.dashboardDefaultSlot || allowedSlots[0];
      if (allowedSlots.length && allowedSlots.indexOf(targetSlotId) === -1) {
        targetSlotId = allowedSlots[0];
      }
      var targetSlot = workspace.querySelector('[data-dashboard-slot-id="' + targetSlotId + '"]');
      if (!targetSlot) {
        return;
      }

      panel.dataset.dashboardHidden = 'false';
      panel.dataset.dashboardCollapsed = 'false';
      panel.dataset.dashboardCurrentSlot = targetSlotId;
      panel.classList.remove('is-hidden');
      panel.classList.remove('is-collapsed');
      targetSlot.appendChild(panel);
      rebuildHiddenTray();
      refreshPanelControls(panel);
      persistCurrentState('Bloco restaurado.');
    }

    function handlePointerDown(event) {
      dragHandlePressed = Boolean(event.target.closest('[data-drag-handle]'));
    }

    function handlePointerUp() {
      dragHandlePressed = false;
    }

    function handleDragStart(event) {
      var panel = event.target.closest('[data-panel-id]');
      if (!isEditing || !panel || !dragHandlePressed) {
        event.preventDefault();
        return;
      }

      draggedPanel = panel;
      draggedPanel.classList.add('is-dragging');
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', panel.dataset.panelId || '');
      }
    }

    function handleDragOver(event) {
      if (!draggedPanel || !isEditing) {
        return;
      }

      var slot = event.target.closest('[data-dashboard-slot-id]');
      if (!slot) {
        return;
      }

      event.preventDefault();
      var afterElement = getDragAfterElement(slot, event.clientY);
      if (!afterElement) {
        slot.appendChild(draggedPanel);
      } else {
        slot.insertBefore(draggedPanel, afterElement);
      }
      draggedPanel.dataset.dashboardCurrentSlot = slot.dataset.dashboardSlotId || slot.dataset.dashboardSlot;
      refreshPanelControls(draggedPanel);
    }

    function handleDragEnd() {
      if (!draggedPanel) {
        return;
      }
      draggedPanel.classList.remove('is-dragging');
      draggedPanel = null;
      dragHandlePressed = false;
      persistCurrentState('Layout salvo.');
    }

    function handleKeydown(event) {
      var handle = event.target.closest('[data-drag-handle]');
      if (!handle) {
        return;
      }

      var panel = handle.closest('[data-panel-id]');
      if (!panel) {
        return;
      }

      if (event.key === 'ArrowUp' && panel.previousElementSibling) {
        event.preventDefault();
        panel.parentElement.insertBefore(panel, panel.previousElementSibling);
        persistCurrentState('Layout salvo.');
      }

      if (event.key === 'ArrowDown' && panel.nextElementSibling) {
        event.preventDefault();
        panel.parentElement.insertBefore(panel.nextElementSibling, panel);
        persistCurrentState('Layout salvo.');
      }
    }

    function init() {
      toggleButton.addEventListener('click', toggleEditing);
      resetButton.addEventListener('click', resetLayout);
      layoutRoot.addEventListener('click', handleRootClick);
      workspace.addEventListener('click', handleWorkspaceClick);
      workspace.addEventListener('pointerdown', handlePointerDown);
      workspace.addEventListener('pointerup', handlePointerUp);
      workspace.addEventListener('dragstart', handleDragStart);
      workspace.addEventListener('dragover', handleDragOver);
      workspace.addEventListener('dragend', handleDragEnd);
      workspace.addEventListener('keydown', handleKeydown);
      rebuildHiddenTray();
      refreshAllControls();
    }

    return {
      init: init,
      applyLayoutState: applyLayoutState,
    };
  }

  window.OctoBoxDashboard = window.OctoBoxDashboard || {};
  window.OctoBoxDashboard.createLayoutController = createDashboardLayoutController;
}());