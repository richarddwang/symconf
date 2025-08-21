Feature: 透過 YAML 創建 configuration
    Background:
        Given 入口 Python 檔案
            ```python: main.py
            parser = TwinConfParser()
            config = parser.parse_args()
            ```

    Scenario: 單個 YAML 設置檔
        Given YAML 檔案
            ```yaml: connection.yaml
            server: 
                host: localhost
                port: 8080
            ```
            
        When 將此 YAML 檔透過 CLI 傳入
            ```bash
            python main.py --config connection.yaml
            ```

        Then 產生 config 物件
            ```python
            >>> print(config)
            >>> {'server': {'host': 'localhost', 'port': 8080}}
            ```

    Scenario: 透過 CLI 同時傳入多個 YAML 設置檔
        多個 YAML 檔案會做 nested merging，且
        - 越後面的檔案優先度越高
        - 當值為 list 時，或直接全部取代而非串聯

        當同時傳入的檔案數多於 2 個時容易變得複雜，建議使用接下來介紹的 "MERGE" 功能

        Given  兩個 YAML 檔案
            ```yaml: connection.yaml
            server: 
                host: localhost
                ports: 
                    - 8080
                    - 8081
            db: postgres
            ```
            ```yaml: connection2.yaml
            server:
                level: DEBUG
                ports:
                    - 9090
            db: 
                provider: postgres
                location: us
            ```

        When 將這兩個 YAML 檔透過 CLI 傳入
            ```bash
            python main.py --config connection.yaml --config connection2.yaml
            ```

        Then 產生 config 物件
            ```python
            >>> print(config)
            >>> {'server': {'host': 'localhost', 'ports': [9090]}, 'db': {'provider': 'postgres', 'location': 'us'}}
            ```

    Scenario: 透過特殊關鍵字 "MERGE" 來合併多項設置
        MERGE 作為特殊鍵，其值可設為設置庫的設置檔路徑(不含擴張子) ，甚至可指涉被參考設置檔中的任一層級的鍵。
        其效果如將 MERGE 替換成其指涉的值，並對其下有衝突的部分做 nested merging 一般。
        注意在處理 YAML 檔時是一行行往下，而越下面的在衝突中越優先
        
        Given YAML 設置庫
            ```yaml: configs/default.yaml
            server: 
                host: localhost
                ports: 
                    - 8080
                    - 8081
            db: postgres
            ```
            ```yaml: configs/server/default.yaml
            default1:
                level: DEBUG
                ports:
                    - 9090
            default2:
                host: default_site.com
                max_requests: 3
            ```

        And YAML 檔
            ```yaml
            MERGE: default
            server:
                host: awesome_site.com
                MERGE: server.default.default2
                level: INFO
                MERGE: server.default.default1.ports
            ```

        And 解析器有定義 YAML 設置庫路徑
            ```python: main.py
            parser = TwinConfParser(config_lib='./configs')
            config = parser.parse_args()
            ```

        When 將 YAML 檔透過 CLI 傳入
            ```bash
            python main.py --config connection.yaml
            ```

        Then 產生 config 物件
            ```python
            >>> print(config)
            >>> {'server': {'host': 'default_site.com', 'ports': [9090], 'max_requests': 3, 'level': 'DEBUG'}, 'db': 'postgres'}
            ```
            在上面的 YAML 檔中， `MERGE: default`, `server: host`, `server: MERGE: server.default.default2` 都有定義 "host"，
            最終 "host" 的值是以最晚出現的 `server: MERGE` 為準。

Feature: 透過 CLI arguments 創建 configuration
    Background:
        Given 入口 Python 檔案
            ```python: main.py
            parser = TwinConfParser(config_lib="configs")
            config = parser.parse_args()
            ```

    Scenario: 混合使用 YAML 檔案和 CLI arguments
        Given YAML 檔案
                ```yaml: connection.yaml
                server: 
                    host: localhost
                    port: 8080
                ```
        When 將 YAML 檔透過 CLI 傳入，並同時指定 CLI arguments
            ```bash
            python main.py --config connection.yaml --server.host awesome_site.com --server.port 9090
            ```
        Then 產生 config 物件
            ```python
            >>> print(config)
            >>> {'server': {'host': 'awesome_site.com', 'port': 9090}}
            ```

    Scenario: 同時使用 MERGE 和 CLI arguments
        透過 CLI 傳入的值優先順序是最高的

        Given YAML 設置庫
            ```yaml: configs/default.yaml
            server: 
                host: localhost
                ports: 
                    - 8080
                    - 8081
            db: postgres
            ```
        And YAML 檔
            ```yaml
            MERGE: default
            server:
                host: awesome_site.com
                level: INFO
            ```
        When 將 YAML 檔透過 CLI 傳入，並同時指定 CLI arguments
            ```bash
            python main.py --config connection.yaml --server.host=cli_site.com --server.ports=[9090,9091]
            ```
        Then 產生 config 物件
            ```python
            >>> print(config)
            >>> {'server': {'host': 'cli_site.com', 'ports': [9090, 9091], 'level': 'INFO'}, 'db': 'postgres'}
            ```