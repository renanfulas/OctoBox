(function() {
  var payloadElement = document.getElementById('current-page-behavior');
  var pagePayload = {};
  if (payloadElement) {
    try {
      pagePayload = JSON.parse(payloadElement.textContent || '{}');
    } catch (error) {
      pagePayload = {};
    }
  }

  var layoutRoot = document.querySelector('[data-dashboard-layout-version]');
  var toolbar = document.querySelector('[data-dashboard-layout-toolbar]');
  var hiddenPool = document.querySelector('[data-dashboard-hidden-pool]');
  var hiddenList = document.querySelector('[data-dashboard-hidden-list]');
  var workspace = document.querySelector('[data-dashboard-workspace]');
  var toggleButton = document.getElementById('toggle-dashboard-layout');
  var resetButton = document.getElementById('reset-dashboard-layout');
  var statusNode = document.getElementById('dashboard-layout-status');
  var saveUrl = pagePayload.dashboard_layout_save_url;
  var factory = window.OctoBoxDashboard && window.OctoBoxDashboard.createLayoutController;

  if (!layoutRoot || !toolbar || !workspace || !toggleButton || !resetButton || !saveUrl || !factory) {
    return;
  }

  factory({
    layoutRoot: layoutRoot,
    toolbar: toolbar,
    workspace: workspace,
    hiddenPool: hiddenPool,
    hiddenList: hiddenList,
    toggleButton: toggleButton,
    resetButton: resetButton,
    statusNode: statusNode,
    saveUrl: saveUrl,
  }).init();
}());