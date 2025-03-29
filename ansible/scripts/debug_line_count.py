from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Debug-Read-Test").getOrCreate()

df = spark.read.text("hdfs:///user/almalinux/datasets/uniref50.fasta")
print("✅ Number of lines in file:", df.count())

spark.stop()
