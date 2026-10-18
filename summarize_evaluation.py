
import pandas as pd

input_file = "multi_cover_evaluation.csv"
output_file = "multi_cover_summary.csv"

df = pd.read_csv(input_file)

summary_columns = [
    "embedding_time_ms",
    "extraction_time_ms",
    "mse",
    "psnr_db",
    "ssim",
    "lsb_one_fraction_change",
]

summary = (
    df.groupby(["cover", "method", "payload_bytes"])[summary_columns]
    .mean()
    .reset_index()
)

print("\n========== AVERAGE RESULTS ==========")
print(summary.to_string(index=False))

summary.to_csv(output_file, index=False)
print(f"\nSummary saved to: {output_file}")
