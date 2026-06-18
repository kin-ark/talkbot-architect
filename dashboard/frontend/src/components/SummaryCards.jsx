export default function SummaryCards({ errors, warnings }) {
  return (
    <div className="grid grid-cols-2 gap-4 mb-8">
      <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded shadow-sm">
        <h3 className="text-red-800 font-bold text-2xl">{errors}</h3>
        <p className="text-red-600 text-sm font-medium">Critical Errors</p>
      </div>
      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded shadow-sm">
        <h3 className="text-amber-800 font-bold text-2xl">{warnings}</h3>
        <p className="text-amber-600 text-sm font-medium">Optimization Warnings</p>
      </div>
    </div>
  );
}
