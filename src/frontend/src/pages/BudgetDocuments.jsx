import { useState, useEffect } from "react";
import { FileText, Trash2, CheckCircle2, Clock, AlertCircle, Eye } from "lucide-react";

const API = "http://localhost:8000";

function BudgetDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDocs();
    const interval = setInterval(fetchDocs, 5000);
    return () => clearInterval(interval);
  }, []);

  async function fetchDocs() {
    try {
      const res = await fetch(`${API}/api/budget/documents`);
      if (!res.ok) throw new Error("Failed to fetch");
      const data = await res.json();
      setDocuments(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  async function handleDelete(docId) {
    if (!confirm("Archive this document? Its vectors will be removed from search."))
      return;
    try {
      await fetch(`${API}/api/budget/documents/${docId}`, { method: "DELETE" });
      fetchDocs();
    } catch (err) {
      alert("Failed to archive: " + err.message);
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case "ready":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
            <CheckCircle2 className="h-3 w-3" />
            Ready
          </span>
        );
      case "uploading":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700">
            <Clock className="h-3 w-3 animate-spin" />
            Processing
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
            <AlertCircle className="h-3 w-3" />
            Failed
          </span>
        );
      case "archived":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
            Archived
          </span>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-slate-400">
        <Clock className="h-5 w-5 animate-spin mr-2" />
        Loading documents...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-500">
        <AlertCircle className="h-8 w-8 mx-auto mb-2" />
        {error}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">
          Budget Documents
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          All uploaded county budget PDFs. Upload new documents from the Upload page.
        </p>
      </div>

      {documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white py-16 text-slate-400 shadow-sm">
          <FileText className="mb-3 h-12 w-12 opacity-50" />
          <p className="text-sm font-medium">No documents uploaded yet</p>
          <p className="text-xs mt-1">
            Go to "Upload Budget PDF" to add your first document
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow transition-shadow"
            >
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="flex-shrink-0">
                  <FileText className="h-8 w-8 text-blue-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-slate-800 truncate">
                      {doc.filename}
                    </h3>
                    {getStatusBadge(doc.status)}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span>{doc.total_pages || "?"} pages</span>
                    <span>{doc.total_chunks || "?"} chunks</span>
                    <span>{doc.size_mb?.toFixed(1)} MB</span>
                    <span>FY {doc.fiscal_year}</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Uploaded: {new Date(doc.uploaded_at).toLocaleDateString()}
                    {doc.completed_at &&
                      ` · Completed: ${new Date(doc.completed_at).toLocaleDateString()}`}
                  </p>
                  {doc.error_message && (
                    <p className="text-xs text-red-500 mt-1 truncate">
                      {doc.error_message}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                  title="Archive document"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default BudgetDocuments;