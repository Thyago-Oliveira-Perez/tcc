import os

if __name__ == "__main__":
    w = os.walk("./kubernetes")

    for root, dirs, files in w:
        for file in files:
            if "\\.git\\" in root:
                continue

            file_path = os.path.join(root, file)

            print(file_path)
            os.system(
                f"""cd kubernetes; git log --pretty=format:"%h - %an, %ad : %s" -- {file_path}""")
