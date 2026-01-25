frappe.pages['cdn-export-dashboard'].on_page_load = function(wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    title: 'CDN Export Dashboard',
    single_column: true
  });

  // Initialize dashboard
  let dashboard = new CDNExportDashboard(wrapper);
  dashboard.init();
};

class CDNExportDashboard {
  constructor(wrapper) {
    this.wrapper = wrapper;
    this.refresh_interval = null;
    this.auto_refresh_enabled = true;
  }

  init() {
    this.setup_event_listeners();
    this.refresh_data();

    // Auto-refresh every 30 seconds
    this.refresh_interval = setInterval(() => {
      if (this.auto_refresh_enabled) {
        this.refresh_data();
      }
    }, 30000);
  }

  setup_event_listeners() {
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
      this.refresh_data();
    });

    // Filter history button
    document.getElementById('filter-history-btn').addEventListener('click', () => {
      this.load_sync_history();
    });

    // Retry all button
    document.getElementById('retry-all-btn').addEventListener('click', () => {
      this.retry_all_dead_letter();
    });

    // Clear dead letter button
    document.getElementById('clear-dead-letter-btn').addEventListener('click', () => {
      this.clear_dead_letter();
    });

    // Allow Enter key in plan filter
    document.getElementById('plan-filter').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.load_sync_history();
      }
    });
  }

  refresh_data() {
    this.load_queue_status();
    this.load_recent_failures();
    this.load_sync_history();
  }

  load_queue_status() {
    frappe.call({
      method: 'memora.api.cdn_admin.get_queue_status',
      callback: (r) => {
        if (r.message) {
          const status = r.message;
          document.getElementById('pending-count').textContent = status.pending_plans || 0;
          document.getElementById('dead-letter-count').textContent = status.dead_letter_count || 0;

          if (status.last_processed) {
            const last_date = frappe.ui.form.utils.format_datetime(status.last_processed);
            document.getElementById('last-processed').textContent = last_date;
          }
        }
      }
    });
  }

  load_recent_failures() {
    frappe.call({
      method: 'memora.api.cdn_admin.get_recent_failures',
      args: {
        limit: 20,
        days: 7
      },
      callback: (r) => {
        if (r.message) {
          this.render_failures_table(r.message);
        }
      }
    });
  }

  render_failures_table(failures) {
    const tbody = document.getElementById('failures-tbody');

    if (!failures || failures.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No failures in the last 7 days</td></tr>';
      return;
    }

    tbody.innerHTML = failures.map(failure => `
      <tr>
        <td><strong>${failure.plan_id}</strong></td>
        <td>
          <span class="badge ${failure.status === 'Dead Letter' ? 'badge-danger' : 'badge-warning'}">
            ${failure.status}
          </span>
        </td>
        <td>${failure.retry_count || 0}</td>
        <td><small>${failure.error_message ? failure.error_message.substring(0, 50) : '--'}</small></td>
        <td><small>${frappe.ui.form.utils.format_datetime(failure.creation)}</small></td>
        <td>
          <button class="btn btn-xs btn-link" onclick="cur_frm && cur_frm.page.page.page_content.dashboard.show_log('${failure.name}')">
            View
          </button>
        </td>
      </tr>
    `).join('');
  }

  load_sync_history() {
    const plan_id = document.getElementById('plan-filter').value.trim() || null;

    frappe.call({
      method: 'memora.api.cdn_admin.get_sync_history',
      args: {
        plan_id: plan_id,
        limit: 50
      },
      callback: (r) => {
        if (r.message) {
          this.render_history_table(r.message);
        }
      }
    });
  }

  render_history_table(history) {
    const tbody = document.getElementById('history-tbody');

    if (!history || history.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No sync history found</td></tr>';
      return;
    }

    tbody.innerHTML = history.map(record => {
      const status_class = record.status === 'Success' ? 'badge-success' :
                          record.status === 'Failed' ? 'badge-danger' :
                          record.status === 'Processing' ? 'badge-info' :
                          record.status === 'Dead Letter' ? 'badge-danger' :
                          'badge-default';

      return `
        <tr>
          <td><strong>${record.plan_id}</strong></td>
          <td>
            <span class="badge ${status_class}">
              ${record.status}
            </span>
          </td>
          <td><small>${record.started_at ? frappe.ui.form.utils.format_datetime(record.started_at) : '--'}</small></td>
          <td><small>${record.completed_at ? frappe.ui.form.utils.format_datetime(record.completed_at) : '--'}</small></td>
          <td>${record.files_uploaded || 0}</td>
          <td>${record.triggered_by || '--'}</td>
        </tr>
      `;
    }).join('');
  }

  retry_all_dead_letter() {
    frappe.confirm('Retry all dead letter items?', () => {
      frappe.call({
        method: 'memora.api.cdn_admin.get_recent_failures',
        args: {
          limit: 1000,
          days: 365
        },
        callback: (r) => {
          if (r.message) {
            const dead_letters = r.message.filter(f => f.status === 'Dead Letter');
            let retried = 0;
            let failed = 0;

            dead_letters.forEach(item => {
              frappe.call({
                method: 'memora.api.cdn_admin.retry_dead_letter',
                args: {
                  sync_log_name: item.name
                },
                callback: (resp) => {
                  if (resp.message && resp.message.success) {
                    retried++;
                  } else {
                    failed++;
                  }

                  if (retried + failed === dead_letters.length) {
                    frappe.msgprint(`Retried ${retried} items, ${failed} failed`);
                    this.refresh_data();
                  }
                }
              });
            });
          }
        }
      });
    });
  }

  clear_dead_letter() {
    frappe.confirm('Clear all dead letter items? This cannot be undone.', () => {
      frappe.call({
        method: 'memora.api.cdn_admin.clear_dead_letter',
        callback: (r) => {
          if (r.message && r.message.success) {
            frappe.msgprint(r.message.message);
            this.refresh_data();
          } else {
            frappe.msgprint('Error clearing dead letter queue');
          }
        }
      });
    });
  }

  show_log(sync_log_name) {
    frappe.call({
      method: 'frappe.client.get',
      args: {
        doctype: 'CDN Sync Log',
        name: sync_log_name
      },
      callback: (r) => {
        if (r.message) {
          // Create a modal to show the log
          let d = new frappe.ui.Dialog({
            title: `Sync Log: ${sync_log_name}`,
            fields: [
              {
                fieldtype: 'Section Break',
                label: 'Sync Details'
              },
              {
                fieldname: 'plan_id',
                fieldtype: 'Link',
                label: 'Plan',
                options: 'Memora Academic Plan',
                read_only: 1,
                default: r.message.plan_id
              },
              {
                fieldname: 'status',
                fieldtype: 'Select',
                label: 'Status',
                read_only: 1,
                default: r.message.status
              },
              {
                fieldname: 'started_at',
                fieldtype: 'Datetime',
                label: 'Started At',
                read_only: 1,
                default: r.message.started_at
              },
              {
                fieldname: 'completed_at',
                fieldtype: 'Datetime',
                label: 'Completed At',
                read_only: 1,
                default: r.message.completed_at
              },
              {
                fieldname: 'retry_count',
                fieldtype: 'Int',
                label: 'Retry Count',
                read_only: 1,
                default: r.message.retry_count
              },
              {
                fieldname: 'error_message',
                fieldtype: 'Small Text',
                label: 'Error Message',
                read_only: 1,
                default: r.message.error_message
              },
              {
                fieldname: 'triggered_by',
                fieldtype: 'Data',
                label: 'Triggered By',
                read_only: 1,
                default: r.message.triggered_by
              }
            ],
            primary_action_label: 'Close',
            primary_action: function() {
              d.hide();
            }
          });

          d.show();
        }
      }
    });
  }

  destroy() {
    if (this.refresh_interval) {
      clearInterval(this.refresh_interval);
    }
  }
}
