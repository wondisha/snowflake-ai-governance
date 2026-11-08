import streamlit as st

def display_setup(session):
    """
    Displays the setup and configuration documentation page in Streamlit.
    
    This function renders a styled documentation page that guides users through setting up
    and configuring the application. It includes sections on prerequisites, repository setup,
    debug mode configuration, local deployment, native Snowflake deployment, troubleshooting,
    and support information.

    Args:
        session: Snowflake session object (unused in this function but kept for consistency)
    """
    # Apply custom CSS styles for consistency
    st.markdown("""
        <style>
            .header-section {
                background-color: #56CCF2;
                padding: 30px;
                text-align: center;
                border-radius: 10px;
                color: white;
                font-family: 'Arial', sans-serif;
            }
            .header-title {
                font-size: 3em;
                font-weight: bold;
            }
            .header-subtitle {
                font-size: 1.2em;
                margin-top: 10px;
            }
            .section {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
                box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
            }
            .section-title {
                font-size: 1.8em;
                font-weight: bold;
                color: #56CCF2;
                margin-bottom: 10px;
            }
            .section-content {
                font-size: 1.1em;
                line-height: 1.5;
                color: #333;
            }
        </style>
    """, unsafe_allow_html=True)

    # Header Section
    st.markdown("""
        <div class="header-section">
            <div class="header-title">Local Setup & Configuration</div>
            <div class="header-subtitle">Learn how to configure and deploy the application</div>
        </div>
    """, unsafe_allow_html=True)

    # Prerequisites Section
    st.markdown("""
        <div class="section">
            <div class="section-title">1. Prerequisites</div>
            <div class="section-content">
                Ensure you meet the following prerequisites before proceeding:
                <ul>
                    <li>An active <strong>Snowflake account</strong> with Cortex functionalities enabled.</li>
                    <li>Account role: <strong>ACCOUNTADMIN</strong> or equivalent with permissions to create stages, databases, and other resources.</li>
                    <li>Python version <strong>3.7+</strong> installed.</li>
                    <li><strong>Streamlit</strong> installed for local testing.</li>
                </ul>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Cloning the Repository Section
    st.markdown("""
        <div class="section">
            <div class="section-title">2. Clone the Repository</div>
            <div class="section-content">
                Clone the application repository and install dependencies:
                <pre><code>
git clone https://github.com/sgsshankar/Snowflake-AI-Toolkit.git
cd snowflake-ai-toolkit
pip install -r requirements.txt
                </code></pre>
                All required dependencies are listed in the <code>requirements.txt</code> file.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Configuring Debug Mode Section
    st.markdown("""
        <div class="section">
            <div class="section-title">3. Configuring Debug Mode</div>
            <div class="section-content">
                Follow these steps to configure the application for Debug Mode:
                <ol>
                    <li>Open the <code>src/settings_config.json</code> file in a text editor.</li>
                    <li>Locate the <code>mode</code> parameter and set its value to <code>"debug"</code>:
                        <pre><code>
    {
        "mode": "debug",
        "snowflake": {
        "account": "your-account-url",
        "user": "your-username",
        "password": "your-password",
        "role": "your-role",
        "warehouse": "your-warehouse",
        "database": "your-database",
        "schema": "your-schema"
        }
    }
                        </code></pre>
                    </li>
                    <li>Save the file after making changes.</li>
                </ol>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Running the App Locally
    st.markdown("""
        <div class="section">
            <div class="section-title">4. Running the Application Locally</div>
            <div class="section-content">
                Launch the app in Debug Mode using the following command:
                <pre><code>streamlit run streamlit_app.py</code></pre>
                After verifying that the app behaves as expected in Debug Mode, you can switch to Native Mode for deployment.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Switching to Native Mode
    st.markdown("""
        <div class="section">
            <div class="section-title">5. Deploying Natively in Snowflake</div>
            <div class="section-content">
                To deploy the application natively in Snowflake:
                <ol>
                    <li>Set the <code>MODE</code> in your <code>settings.json</code> file to <code>native</code>.</li>
                    <li>Use the following command to deploy:
                        <pre><code>
snow streamlit deploy --account "your_account" --user "your_username" --password "your_password" --role "your_role" --warehouse "your_warehouse" --database "your_database" --replace
                        </code></pre>
                        Replace placeholders (<code>&lt;your_account&gt;</code>, etc.) with your actual Snowflake account details.
                    </li>
                    <li>No additional dependency installation is required for running natively in Snowflake.</li>
                </ol>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Troubleshooting Section
    st.markdown("""
        <div class="section">
            <div class="section-title">6. Troubleshooting</div>
            <div class="section-content">
                Common issues and solutions:
                <ul>
                    <li><strong>Permission errors:</strong> Ensure your Snowflake role has the necessary privileges.</li>
                    <li><strong>Dependency issues:</strong> Reinstall dependencies using <code>pip install -r requirements.txt</code>.</li>
                    <li><strong>Configuration issues:</strong> Verify that the <code>.env</code> file is correctly set up.</li>
                </ul>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Support Section
    st.markdown("""
        <div class="section">
            <div class="section-title">7. Support</div>
            <div class="section-content">
                For further assistance, please reach out to the project maintainers or open an issue on GitHub.
            </div>
        </div>
    """, unsafe_allow_html=True)
