/** Export an array of objects as a CSV download. */
export function downloadCsv(rows: Record<string, unknown>[], filename: string) {
	if (rows.length === 0) return;

	const keys = Object.keys(rows[0]);
	const header = keys.join(',');
	const body = rows
		.map((row) =>
			keys
				.map((k) => {
					const v = row[k];
					if (v == null) return '';
					const s = String(v);
					return s.includes(',') || s.includes('"') || s.includes('\n')
						? `"${s.replace(/"/g, '""')}"`
						: s;
				})
				.join(',')
		)
		.join('\n');

	const blob = new Blob([header + '\n' + body], { type: 'text/csv;charset=utf-8;' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	a.click();
	URL.revokeObjectURL(url);
}
