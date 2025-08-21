Feature: Value interpolation
    此功能類似於 Python 的 f-string 功能，只是我們使用 bash 風格的 syntax。

    相對於有些設置架構會在使用該值時才進行替換，TwinConf 在產生設置物件時就會將 placeholder 替換為真正的值。
    順序上來說，會等到所有設置 (YAML檔案、MERGE、CLI 參數) 都合併完後才會進行替換。

    Background:
        Given 入口 Python 檔案
            ```python: main.py
            parser = TwinConfParser(config_lib="configs")
            config = parser.parse_args()
            ```

    Scenario: 代換為其他設置的值
        Given YAML 檔案
            ```yaml: training.yaml
            dataset:
                num_classes: 10
            model: 
                output_features: ${dataset.num_classes} 
                random_seed: 1
            log:
                name: seed=${model.random_seed}
            ```

        When 將此 YAML 檔透過 CLI 傳入
            ```bash
            python main.py --config training.yaml
            ```

        Then 產生 config 物件
            ```python
            >>> print(config)
            >>> {'dataset': {'num_classes': 10}, 'model': {'output_features': 10, 'random_seed': 1}, 'log': {'name': 'seed=1'}}
            ```

    Scenario: 代換為環境變數的值
        除了可以指涉設置檔的值，還可以指涉環境變數，
        若指涉的變數不是任何 TwinConf 的設定值時，TwinConf 會自動從環境變數中讀取該值。

        在這個例子中，也展示了如何 TwinConf 可以混合既有環境變數和透過 dotenv 檔傳入的環境變數，
        並優先 dotenv 檔傳入的環境變數

        Given dotenv 檔
            ```dotenv:.env
            HOST=awesome_site.com
            PASSWORD=123
            ```
            ```dotenv:.env2
            PASSWORD=1234
            ```

        And YAML 檔
            ```yaml: connection.yaml
            host: ${HOST}
            password: pw-${PASSWORD}
            ```

        When 讀取
            ```bash
            HOST=default.com python main.py --env=./.env --env=./.env2 --config=connection.yaml
            ```

        Then 環境變數被讀取
            ```python
            >>> import os
            >>> print(os.environ['HOST'])
            >>> 'awesome_site.com'
            >>> print(os.environ['PASSWORD'])
            >>> '1234'
            ```

        And 產生 config 物件
            ```python
            >>> print(config)
            >>> {'HOST': 'awesome_site.com', 'password': 'pw-1234'}
            ```

    Scenario: 代換為 Python expression 的結果
        TwinConf 也支援使用 Python expression 來計算值， 語法為
        - "${}": 包住 expression
        - "``": 在 expression 中包住參數，參數可以是設置變數或環境變數

        Given YAML 檔
            ```yaml: training.yaml
            dataset:
                num_classes: 10
            model: 
                output_features: ${`dataset.num_classes` + `model.extra_outputs`} 
                extra_outputs: 2
            ```

        When 將此 YAML 檔透過 CLI 傳入
            ```bash
            python main.py --config training.yaml
            ```

        Then 產生 config 物件
            ```python
            >>> print(config)
            >>> {'dataset': {'num_classes': 10}, 'model': {'output_features': 12, 'extra_outputs': 2}}
            ```