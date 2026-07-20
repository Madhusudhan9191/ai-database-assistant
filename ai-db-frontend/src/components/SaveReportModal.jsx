import { useState, useEffect } from "react";
import "./SaveReportModal.css";

function SaveReportModal({ isOpen, onClose, onSave, defaultName }) {
  const [reportName, setReportName] = useState("");

  useEffect(() => {
    if (isOpen) {
      setReportName(defaultName || "");
    }
  }, [isOpen, defaultName]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (reportName.trim()) {
      onSave(reportName.trim());
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>⭐ Save Custom Report</h3>
          <button className="modal-close-btn" onClick={onClose}>
            &times;
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <label htmlFor="reportNameInput">Report Name</label>
            <input
              id="reportNameInput"
              type="text"
              value={reportName}
              onChange={(e) => setReportName(e.target.value)}
              placeholder="e.g. Monthly Revenue"
              autoFocus
              required
            />
            <p className="modal-help">
              This report will be saved to your dashboard portfolio under the active database fingerprint.
            </p>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-save">
              Save Report
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SaveReportModal;
