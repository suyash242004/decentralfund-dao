// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title DecentralFund DAO - Demo Smart Contracts
 * @dev Standalone contracts for hackathon demo (no external dependencies)
 */

/**
 * @title FUND Token - Governance Token with Quadratic Voting
 */
contract FUNDToken {
    string public name = "DecentralFund DAO Token";
    string public symbol = "FUND";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => uint256) public votingPower;
    
    address public owner;
    bool public paused = false;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event VotingPowerUpdated(address indexed account, uint256 oldPower, uint256 newPower);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }
    
    modifier whenNotPaused() {
        require(!paused, "Contract is paused");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1000000 * 10**decimals; // 1 million initial supply
        balanceOf[msg.sender] = totalSupply;
        _updateVotingPower(msg.sender);
    }
    
    /**
     * @dev Mint tokens (only for SIP investments)
     */
    function mint(address to, uint256 amount) external onlyOwner whenNotPaused {
        require(to != address(0), "Cannot mint to zero address");
        
        totalSupply += amount;
        balanceOf[to] += amount;
        _updateVotingPower(to);
        
        emit Transfer(address(0), to, amount);
    }
    
    /**
     * @dev Standard ERC20 transfer
     */
    function transfer(address to, uint256 amount) external whenNotPaused returns (bool) {
        require(to != address(0), "Cannot transfer to zero address");
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        
        _updateVotingPower(msg.sender);
        _updateVotingPower(to);
        
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    /**
     * @dev Calculate quadratic voting power: sqrt(token_balance)
     */
    function _updateVotingPower(address account) internal {
        uint256 balance = balanceOf[account];
        uint256 oldPower = votingPower[account];
        uint256 newPower = _sqrt(balance);
        
        votingPower[account] = newPower;
        emit VotingPowerUpdated(account, oldPower, newPower);
    }
    
    /**
     * @dev Get voting power for an account
     */
    function getVotingPower(address account) external view returns (uint256) {
        return votingPower[account];
    }
    
    /**
     * @dev Square root calculation for voting power
     */
    function _sqrt(uint256 x) internal pure returns (uint256) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        uint256 y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
        return y;
    }
    
    /**
     * @dev Pause contract (emergency only)
     */
    function pause() external onlyOwner {
        paused = true;
    }
    
    /**
     * @dev Unpause contract
     */
    function unpause() external onlyOwner {
        paused = false;
    }
}

/**
 * @title Proposal Manager - DAO Governance
 */
contract ProposalManager {
    FUNDToken public fundToken;
    address public owner;
    
    enum ProposalStatus { Active, Passed, Rejected, Executed, Expired }
    
    struct Proposal {
        uint256 id;
        address creator;
        string title;
        string description;
        string[] options;
        uint256 createdAt;
        uint256 votingEndTime;
        uint256 totalVotes;
        uint256 totalVotingPower;
        mapping(uint256 => uint256) optionVotes; // optionIndex => votes
        mapping(address => bool) hasVoted;
        ProposalStatus status;
        uint256 minimumQuorum;
    }
    
    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;
    uint256 public constant VOTING_DURATION = 7 days;
    uint256 public constant MINIMUM_QUORUM = 1000;
    
    event ProposalCreated(uint256 indexed proposalId, address indexed creator, string title);
    event VoteCast(uint256 indexed proposalId, address indexed voter, uint256 option, uint256 votingPower);
    event ProposalExecuted(uint256 indexed proposalId, uint256 winningOption);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }
    
    constructor(address _fundToken) {
        fundToken = FUNDToken(_fundToken);
        owner = msg.sender;
    }
    
    /**
     * @dev Create a new proposal
     */
    function createProposal(
        string calldata title,
        string calldata description,
        string[] calldata options
    ) external returns (uint256) {
        require(bytes(title).length > 0, "Title cannot be empty");
        require(options.length >= 2, "Must have at least 2 options");
        require(fundToken.balanceOf(msg.sender) >= 100 * 10**18, "Minimum 100 FUND tokens required");
        
        uint256 proposalId = proposalCount++;
        Proposal storage proposal = proposals[proposalId];
        
        proposal.id = proposalId;
        proposal.creator = msg.sender;
        proposal.title = title;
        proposal.description = description;
        proposal.options = options;
        proposal.createdAt = block.timestamp;
        proposal.votingEndTime = block.timestamp + VOTING_DURATION;
        proposal.status = ProposalStatus.Active;
        proposal.minimumQuorum = MINIMUM_QUORUM;
        
        emit ProposalCreated(proposalId, msg.sender, title);
        return proposalId;
    }
    
    /**
     * @dev Cast a vote on a proposal
     */
    function vote(uint256 proposalId, uint256 option, uint256 votingPowerToUse) external {
        Proposal storage proposal = proposals[proposalId];
        
        require(proposal.status == ProposalStatus.Active, "Proposal not active");
        require(block.timestamp <= proposal.votingEndTime, "Voting period ended");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        require(option < proposal.options.length, "Invalid option");
        
        uint256 voterPower = fundToken.getVotingPower(msg.sender);
        require(voterPower >= votingPowerToUse, "Insufficient voting power");
        require(votingPowerToUse > 0, "Must use some voting power");
        
        proposal.hasVoted[msg.sender] = true;
        proposal.optionVotes[option] += votingPowerToUse;
        proposal.totalVotes += 1;
        proposal.totalVotingPower += votingPowerToUse;
        
        emit VoteCast(proposalId, msg.sender, option, votingPowerToUse);
        
        // Auto-finalize if voting ended
        if (block.timestamp > proposal.votingEndTime) {
            _finalizeProposal(proposalId);
        }
    }
    
    /**
     * @dev Finalize a proposal after voting period
     */
    function finalizeProposal(uint256 proposalId) external {
        _finalizeProposal(proposalId);
    }
    
    function _finalizeProposal(uint256 proposalId) internal {
        Proposal storage proposal = proposals[proposalId];
        
        require(proposal.status == ProposalStatus.Active, "Proposal not active");
        require(block.timestamp > proposal.votingEndTime, "Voting still ongoing");
        
        if (proposal.totalVotingPower < proposal.minimumQuorum) {
            proposal.status = ProposalStatus.Rejected;
            return;
        }
        
        // Find winning option
        uint256 winningOption = 0;
        uint256 maxVotes = proposal.optionVotes[0];
        
        for (uint256 i = 1; i < proposal.options.length; i++) {
            if (proposal.optionVotes[i] > maxVotes) {
                maxVotes = proposal.optionVotes[i];
                winningOption = i;
            }
        }
        
        proposal.status = ProposalStatus.Passed;
        emit ProposalExecuted(proposalId, winningOption);
    }
    
    /**
     * @dev Get proposal results
     */
    function getProposalResults(uint256 proposalId) 
        external 
        view 
        returns (uint256 winningOption, uint256 totalVotes, uint256 totalVotingPower, bool isFinalized) 
    {
        Proposal storage proposal = proposals[proposalId];
        
        uint256 maxVotes = proposal.optionVotes[0];
        winningOption = 0;
        
        for (uint256 i = 1; i < proposal.options.length; i++) {
            if (proposal.optionVotes[i] > maxVotes) {
                maxVotes = proposal.optionVotes[i];
                winningOption = i;
            }
        }
        
        return (winningOption, proposal.totalVotes, proposal.totalVotingPower, proposal.status != ProposalStatus.Active);
    }
    
    /**
     * @dev Get votes for a specific option
     */
    function getOptionVotes(uint256 proposalId, uint256 option) external view returns (uint256) {
        return proposals[proposalId].optionVotes[option];
    }
}

/**
 * @title SIP Manager - Systematic Investment Plans
 */
contract SIPManager {
    FUNDToken public fundToken;
    address public owner;
    address public feeRecipient;
    
    enum SIPStatus { Active, Paused, Cancelled, Completed }
    
    struct SIPPlan {
        uint256 id;
        address investor;
        uint256 amountPerInstallment;
        uint256 frequency; // in seconds
        uint256 startDate;
        uint256 endDate;
        uint256 nextPaymentDate;
        uint256 totalInvested;
        uint256 totalTokensReceived;
        uint256 installmentsPaid;
        SIPStatus status;
        bool autoCompound;
    }
    
    mapping(uint256 => SIPPlan) public sipPlans;
    mapping(address => uint256[]) public userSIPs;
    uint256 public sipCount;
    
    // Fee structure (in basis points, 100 = 1%)
    uint256 public managementFeePercentage = 100; // 1.00%
    
    event SIPCreated(uint256 indexed sipId, address indexed investor, uint256 amountPerInstallment, uint256 frequency);
    event SIPPaymentProcessed(uint256 indexed sipId, address indexed investor, uint256 amount, uint256 tokensReceived);
    event SIPStatusChanged(uint256 indexed sipId, SIPStatus oldStatus, SIPStatus newStatus);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }
    
    constructor(address _fundToken, address _feeRecipient) {
        fundToken = FUNDToken(_fundToken);
        feeRecipient = _feeRecipient;
        owner = msg.sender;
    }
    
    /**
     * @dev Create a new SIP plan
     */
    function createSIP(
        uint256 amountPerInstallment,
        uint256 frequency,
        uint256 duration,
        bool autoCompound
    ) external payable returns (uint256) {
        require(amountPerInstallment >= 10 * 10**18, "Minimum $10 per installment");
        require(frequency >= 1 days, "Minimum frequency is 1 day");
        require(msg.value >= amountPerInstallment, "Insufficient payment for first installment");
        
        uint256 sipId = sipCount++;
        uint256 endDate = duration > 0 ? block.timestamp + duration : 0; // 0 means unlimited
        
        SIPPlan storage sip = sipPlans[sipId];
        sip.id = sipId;
        sip.investor = msg.sender;
        sip.amountPerInstallment = amountPerInstallment;
        sip.frequency = frequency;
        sip.startDate = block.timestamp;
        sip.endDate = endDate;
        sip.nextPaymentDate = block.timestamp + frequency;
        sip.status = SIPStatus.Active;
        sip.autoCompound = autoCompound;
        
        userSIPs[msg.sender].push(sipId);
        
        // Process first payment
        _processSIPPayment(sipId, amountPerInstallment);
        
        emit SIPCreated(sipId, msg.sender, amountPerInstallment, frequency);
        return sipId;
    }
    
    /**
     * @dev Process SIP payment (internal)
     */
    function _processSIPPayment(uint256 sipId, uint256 amount) internal {
        SIPPlan storage sip = sipPlans[sipId];
        
        // Calculate fees
        uint256 managementFee = (amount * managementFeePercentage) / 10000;
        uint256 netAmount = amount - managementFee;
        
        // Calculate tokens to mint (simplified: 1 token = 1 USD)
        uint256 tokensToMint = netAmount;
        
        // Mint tokens to investor
        fundToken.mint(sip.investor, tokensToMint);
        
        // Send fee to fee recipient
        if (managementFee > 0) {
            payable(feeRecipient).transfer(managementFee);
        }
        
        // Update SIP statistics
        sip.totalInvested += amount;
        sip.totalTokensReceived += tokensToMint;
        sip.installmentsPaid += 1;
        
        emit SIPPaymentProcessed(sipId, sip.investor, amount, tokensToMint);
    }
    
    /**
     * @dev Get user's SIP plans
     */
    function getUserSIPs(address user) external view returns (uint256[] memory) {
        return userSIPs[user];
    }
    
    /**
     * @dev Get SIP plan details
     */
    function getSIPPlan(uint256 sipId) external view returns (
        address investor,
        uint256 amountPerInstallment,
        uint256 frequency,
        uint256 totalInvested,
        uint256 totalTokensReceived,
        SIPStatus status
    ) {
        SIPPlan storage sip = sipPlans[sipId];
        return (
            sip.investor,
            sip.amountPerInstallment,
            sip.frequency,
            sip.totalInvested,
            sip.totalTokensReceived,
            sip.status
        );
    }
}

/**
 * @title Fund Manager Registry
 */
contract FundManagerRegistry {
    FUNDToken public fundToken;
    address public owner;
    
    struct FundManager {
        address managerAddress;
        string name;
        string credentials;
        uint256 experienceYears;
        uint256 votesReceived;
        uint256 termStartDate;
        uint256 termEndDate;
        bool isActive;
        uint256 assetsUnderManagement;
        int256 performanceScore;
    }
    
    mapping(address => FundManager) public fundManagers;
    address[] public activeFundManagers;
    uint256 public constant TERM_DURATION = 90 days;
    uint256 public constant MAX_FUND_MANAGERS = 7;
    
    event FundManagerRegistered(address indexed manager, string name);
    event FundManagerActivated(address indexed manager);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }
    
    constructor(address _fundToken) {
        fundToken = FUNDToken(_fundToken);
        owner = msg.sender;
    }
    
    /**
     * @dev Register as a fund manager candidate
     */
    function registerFundManager(
        string calldata name,
        string calldata credentials,
        uint256 experienceYears
    ) external {
        require(bytes(name).length > 0, "Name cannot be empty");
        require(experienceYears > 0, "Experience required");
        require(fundToken.balanceOf(msg.sender) >= 1000 * 10**18, "Minimum 1000 FUND tokens required");
        
        FundManager storage manager = fundManagers[msg.sender];
        manager.managerAddress = msg.sender;
        manager.name = name;
        manager.credentials = credentials;
        manager.experienceYears = experienceYears;
        
        emit FundManagerRegistered(msg.sender, name);
    }
    
    /**
     * @dev Get active fund managers
     */
    function getActiveFundManagers() external view returns (address[] memory) {
        return activeFundManagers;
    }
}